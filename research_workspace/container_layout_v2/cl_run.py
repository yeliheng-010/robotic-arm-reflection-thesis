"""四卡分片；每条件新进程，程序错误停止该分片。"""
import argparse
import os
import subprocess
import sys
import time
from cl_common import read, save, verify
from cl_design import ROOT, SHARDS, SMOKE_SEEDS, WORKER_SECONDS


def indices(plan, phase):
    return [i for i,r in enumerate(plan['items']) if
            (r['seed'] in SMOKE_SEEDS)==(phase=='smoke')]


def run(phase, shard):
    assert os.environ.get('SLURM_JOB_ID')
    plan = verify()
    if phase=='batch':
        assert read(ROOT/'gate_smoke.json')['passed']
    selected = indices(plan, phase)[shard::SHARDS]
    path = ROOT/'stages'/phase/f'{shard}.json'
    assert not path.exists(), 'No silent retries'
    status = dict(status='running', phase=phase, shard=shard, expected=len(selected),
        completed=0, indices=[], started_at=time.time(), job=os.environ['SLURM_JOB_ID'])
    save(path, status)
    try:
        for index in selected:
            item = plan['items'][index]
            log = ROOT/'logs'/f"{item['id']}.log"
            log.parent.mkdir(exist_ok=True)
            with log.open('x') as stream:
                subprocess.run([sys.executable,str(ROOT/'cl_worker.py'),str(index)],
                    stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=WORKER_SECONDS)
            assert read(ROOT/'runs'/item['id']/'summary.json')['passed']
            status['indices'].append(index)
            status['completed']+=1
            save(path,status)
        verify()
        status['status']='completed'
    except BaseException as error:
        status.update(status='failed', error=repr(error))
        raise
    finally:
        status['ended_at']=time.time()
        save(path,status)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=('smoke','batch'))
    parser.add_argument('shard',type=int,choices=range(SHARDS))
    args=parser.parse_args()
    run(args.phase,args.shard)
