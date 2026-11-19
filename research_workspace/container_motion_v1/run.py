"""四卡独立进程；任何部分输出都阻止自动重跑。"""
import argparse
import os
import subprocess
import sys
import time
from cm_common import ROOT, SHARDS, verify, read, save, gate

WORKER_TIMEOUT = 900


def indices(manifest, phase):
    if phase=='development':
        return list(range(len(manifest['cases'])))
    count = len(manifest['validation_plan']['items'])
    return list(range(4)) if phase=='smoke' else list(range(4,count))


def execute(index, phase, manifest):
    is_dev = phase=='development'
    item = manifest['cases'][index]['source']['item'] if is_dev else manifest['validation_plan']['items'][index]
    folder = ROOT/('development' if is_dev else 'validation')/item['id']
    assert not folder.exists(), 'Partial condition requires diagnosis'
    (ROOT/'logs').mkdir(exist_ok=True)
    with (ROOT/'logs'/f'{phase}_{index:03d}.log').open('x') as stream:
        subprocess.run([sys.executable,str(ROOT/'cm_worker.py'),phase,str(index)],check=True,
            stdout=stream,stderr=subprocess.STDOUT,timeout=WORKER_TIMEOUT)
    result = read(folder/'result.json')
    assert result['status']=='completed' and result['index']==index


def main(phase, shard):
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify()
    if phase!='development':
        assert gate('gate_development.json')['promote']
    if phase=='batch':
        gate('gate_smoke.json')
    selected = indices(manifest,phase)[shard::SHARDS]
    path = ROOT/'stages'/phase/f'{shard}.json'
    assert not path.exists()
    status = dict(status='running',indices=selected,completed=0,expected=len(selected),
        job=os.environ['SLURM_JOB_ID'],started_at=time.time())
    save(path,status)
    try:
        for index in selected:
            execute(index,phase,manifest)
            status['completed'] += 1
            save(path,status)
        status['status']='completed'
    except BaseException as error:
        status.update(status='failed',error=repr(error))
        raise
    finally:
        status['ended_at']=time.time()
        save(path,status)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase',choices=('development','smoke','batch'))
    parser.add_argument('--shard',type=int,choices=range(SHARDS),required=True)
    args = parser.parse_args()
    main(args.phase,args.shard)
