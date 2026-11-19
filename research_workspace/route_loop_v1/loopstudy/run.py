"""Slurm双分片，每片两个独立进程；阶段门槛后复用冒烟。"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess
import time
from stability.collection_status import atomic
from refinement.config import SIM_PYTHON,WORKER_TIMEOUT
from loopstudy.design import ROOT,ANCHOR_SEED
from loopstudy.protocol import verify
from loopstudy.audit import audit

SHARDS = 2
WORKERS = 2


def worker(index):
    from loopstudy.episode import run
    item = verify()['items'][index]
    directory = ROOT/'tasks'/item['id']
    result = run(item,directory)
    checked = audit(result,item)
    row = dict(id=item['id'],arm=item['arm'],seed=item['seed'],factor=item['factor'],
        success=result['success'],status=result['status'],audit=checked,**{k:v for k,v in checked.items() if k!='passed'})
    atomic(directory/'summary.json',row)


def execute(pair):
    index,item = pair
    directory = ROOT/'tasks'/item['id']
    if (directory/'summary.json').exists():
        result = json.loads((directory/'result.json').read_text())
        row = json.loads((directory/'summary.json').read_text())
        assert row['audit']==audit(result,item)
        return row
    with (ROOT/'logs'/f"{item['id']}.log").open('x') as stream:
        subprocess.run([SIM_PYTHON,'-m','loopstudy.run','--index',str(index)],stdout=stream,
            stderr=subprocess.STDOUT,check=True,timeout=WORKER_TIMEOUT*3)
    return json.loads((directory/'summary.json').read_text())


def gate():
    rows = []
    for shard in range(SHARDS):
        saved = json.loads((ROOT/'smoke'/f'shard_{shard}'/'progress.json').read_text())
        assert saved['status']=='completed' and saved['completed']==4
        rows.extend(saved['rows'])
    assert not any(r['invalid'] or r['service_errors'] for r in rows)
    assert sum(r['success'] for r in rows if r['arm']=='new_rule')==2


def run(phase,shard):
    from flashnext.client import ready
    items = verify()['items']
    if phase=='batch':
        gate()
    order = [(i,r) for i,r in enumerate(items) if i%SHARDS==shard and
             (phase=='batch' or r['seed']==ANCHOR_SEED)]
    output = ROOT/phase/f'shard_{shard}'
    output.mkdir(parents=True,exist_ok=False)
    (ROOT/'logs').mkdir(exist_ok=True)
    status = dict(status='running',expected=len(order),completed=0,rows=[],models=ready(),
                  job=os.environ['SLURM_JOB_ID'],array_job=os.environ.get('SLURM_ARRAY_JOB_ID'))
    atomic(output/'progress.json',status)
    try:
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            for start in range(0,len(order),WORKERS):
                rows = list(pool.map(execute,order[start:start+WORKERS]))
                status['rows'].extend(rows)
                status['completed']+=len(rows)
                atomic(output/'progress.json',status)
                assert not any(r['service_errors'] for r in rows), 'Service error; preserve and stop'
        verify()
        status['status']='completed'
    except BaseException as error:
        status.update(status='failed',error=repr(error))
        raise
    finally:
        status['ended_at']=time.time()
        atomic(output/'progress.json',status)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--index',type=int)
    parser.add_argument('--phase',choices=('smoke','batch'))
    parser.add_argument('--shard',type=int,choices=range(SHARDS))
    args=parser.parse_args()
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    worker(args.index) if args.index is not None else run(args.phase,args.shard)
