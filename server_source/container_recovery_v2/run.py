"""三卡仿真；成功初态直接记账，失败恢复使用独立进程。"""
import argparse
import os
import subprocess
import sys
import time
from rc_common import ROOT,SHARDS,WORKER_SECONDS,verify,read,save


def indices(manifest,phase):
    return [i for i in range(len(manifest['rows'])) if (i in manifest['smoke'])==(phase=='smoke')]


def execute_condition(index,manifest):
    source=manifest['rows'][index]
    if source['success']:
        from rc_worker import execute
        execute(index,manifest)
    else:
        log=ROOT/'logs'/f"{source['item']['id']}.log"
        log.parent.mkdir(exist_ok=True)
        with log.open('x') as stream:
            subprocess.run([sys.executable,str(ROOT/'rc_worker.py'),str(index)],
                stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=WORKER_SECONDS)
    assert read(ROOT/'tasks'/source['item']['id']/'summary.json')['passed']


def run(phase,shard):
    assert os.environ.get('SLURM_JOB_ID')
    manifest=verify()
    if phase=='batch':
        assert read(ROOT/'gate_smoke.json')['passed']
    selected=indices(manifest,phase)[shard::SHARDS]
    path=ROOT/'stages'/phase/f'{shard}.json'
    assert not path.exists()
    status=dict(status='running',phase=phase,shard=shard,expected=len(selected),
        completed=0,indices=[],started_at=time.time(),job=os.environ['SLURM_JOB_ID'])
    save(path,status)
    try:
        for index in selected:
            execute_condition(index,manifest)
            status['completed']+=1
            status['indices'].append(index)
            save(path,status)
        verify()
        status['status']='completed'
    except BaseException as error:
        status.update(status='failed',error=repr(error))
        raise
    finally:
        status['ended_at']=time.time()
        save(path,status)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=('smoke','batch'))
    parser.add_argument('--shard',type=int,choices=range(SHARDS),required=True)
    args=parser.parse_args()
    run(args.phase,args.shard)
