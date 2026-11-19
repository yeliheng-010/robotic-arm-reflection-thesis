"""三分片分别运行rule/base/tuned，冒烟复用且不重做失败任务。"""
import argparse
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from common import ROOT,PARENT,read,save,verify,is_smoke,sha
from client import ready
from audit_task import audit

SHARDS=3
WORKERS=2
SIM=str(PARENT/'env_sim/bin/python')


def wait_ready():
    deadline=time.monotonic()+180
    while True:
        try:
            return ready()
        except Exception:
            if time.monotonic()>=deadline:
                raise
            time.sleep(3)


def execute(pair):
    index,entry=pair
    folder=ROOT/'tasks'/entry['uid']
    if (folder/'summary.json').exists():
        summary=read(folder/'summary.json')
        if summary['executed']:
            assert summary['audit']==audit(read(folder/'result.json'),entry)
    else:
        assert not folder.exists(),'Partial task must be diagnosed, not silently retried'
        with (ROOT/'logs'/f"{entry['uid']}.log").open('x') as stream:
            subprocess.run([SIM,str(ROOT/'worker.py'),str(index)],check=True,timeout=900,
                           stdout=stream,stderr=subprocess.STDOUT)
        summary=read(folder/'summary.json')
    return summary


def run(phase,shard):
    manifest=verify()
    if phase=='batch':
        gate=read(ROOT/'gate_smoke.json')
        assert gate['status']=='ready'
        assert gate['manifest_sha256']==sha(ROOT/'manifest.json')
    order=[(i,e) for i,e in enumerate(manifest['entries'])
           if i%SHARDS==shard and (phase=='batch' or is_smoke(e))]
    directory=ROOT/'stages'/phase/f'shard_{shard}'
    directory.mkdir(parents=True,exist_ok=False)
    (ROOT/'logs').mkdir(exist_ok=True)
    status=dict(status='running',expected=len(order),completed=0,rows=[],started_at=time.time(),
                job=os.environ['SLURM_JOB_ID'])
    save(directory/'progress.json',status)
    try:
        status['service']=wait_ready()
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            for start in range(0,len(order),WORKERS):
                rows=list(pool.map(execute,order[start:start+WORKERS]))
                status['rows'].extend(rows)
                status['completed']+=len(rows)
                save(directory/'progress.json',status)
                assert not any(r['service_errors'] for r in rows),'Service failure blocks continuation'
        status['status']='completed'
    except BaseException as error:
        status.update(status='failed',error=repr(error))
        raise
    finally:
        status['ended_at']=time.time()
        save(directory/'progress.json',status)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['smoke','batch'])
    parser.add_argument('--shard',type=int,required=True,choices=range(SHARDS))
    args=parser.parse_args()
    assert os.environ.get('SLURM_JOB_ID')
    run(args.phase,args.shard)
