"""两卡每卡两隔离worker，前置审计失败禁止启动后继。"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess
import time
from stability.collection_status import atomic
from refinement.config import SIM_PYTHON,WORKER_TIMEOUT
from hardstudy.design import ROOT,is_smoke
from hardstudy.protocol import verify
from hardstudy import qualify,tasks

SHARDS=2
WORKERS=2
PHASES=('qual_smoke','qualification','loop_smoke','batch')
REQUIRED={'qualification':'qual_smoke','loop_smoke':'qualification','batch':'loop_smoke'}


def entries(phase):
    protocol=verify()
    rows=protocol['scenes' if phase in ('qual_smoke','qualification') else 'items']
    return [(i,r) for i,r in enumerate(rows) if 'smoke' not in phase or is_smoke(r)]


def worker(phase,index):
    protocol=verify()
    if phase in ('qual_smoke','qualification'):
        qualify.run(protocol['scenes'][index])
    else:
        tasks.execute(protocol['items'][index])


def execute(phase,pair):
    index,item=pair
    is_qualification=phase in ('qual_smoke','qualification')
    folder=ROOT/('qualification' if is_qualification else 'tasks')/item['id']
    if (folder/'summary.json').exists():
        if is_qualification:
            qualify.audit(json.loads((folder/'result.json').read_text()),item)
        else:
            tasks.read(item)
    else:
        with (ROOT/'logs'/f"{phase}_{item['id']}.log").open('x') as stream:
            subprocess.run([SIM_PYTHON,'-m','hardstudy.run','--phase',phase,'--index',str(index)],
                stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=WORKER_TIMEOUT*3)
    return json.loads((folder/'summary.json').read_text())


def run(phase,shard):
    if phase in REQUIRED:
        value=json.loads((ROOT/f'gate_{REQUIRED[phase]}.json').read_text())
        assert value['status']=='ready'
    order=[pair for position,pair in enumerate(entries(phase)) if position%SHARDS==shard]
    directory=ROOT/'stages'/phase/f'shard_{shard}'
    directory.mkdir(parents=True,exist_ok=False)
    (ROOT/'logs').mkdir(exist_ok=True)
    status=dict(status='running',expected=len(order),completed=0,rows=[],started_at=time.time(),
                job=os.environ['SLURM_JOB_ID'],array_job=os.environ.get('SLURM_ARRAY_JOB_ID'))
    atomic(directory/'progress.json',status)
    try:
        if phase in ('loop_smoke','batch'):
            from flashnext.client import ready
            status['models']=ready()
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            for start in range(0,len(order),WORKERS):
                rows=list(pool.map(lambda pair:execute(phase,pair),order[start:start+WORKERS]))
                status['rows'].extend(rows)
                status['completed']+=len(rows)
                atomic(directory/'progress.json',status)
                assert not any(r.get('service_errors') for r in rows), 'Service failure; preserve and stop'
        verify()
        status['status']='completed'
    except BaseException as error:
        status.update(status='failed',error=repr(error))
        raise
    finally:
        status['ended_at']=time.time()
        atomic(directory/'progress.json',status)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--phase',choices=PHASES,required=True)
    parser.add_argument('--shard',type=int,choices=range(SHARDS))
    parser.add_argument('--index',type=int)
    args=parser.parse_args()
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    worker(args.phase,args.index) if args.index is not None else run(args.phase,args.shard)
