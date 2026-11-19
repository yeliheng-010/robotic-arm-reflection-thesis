"""四卡分片，冒烟与批量互斥，禁止隐式重试。"""
import argparse
import os
import subprocess
import sys
import time
from cd_common import ROOT, SHARDS, verify, read, save, gate
from cd_physics_audit import audit_result

BRANCH_TIMEOUT = 300


def indices(manifest, phase):
    if phase == 'smoke':
        return manifest['smoke']
    return [r['index'] for r in manifest['branches'] if r['index'] not in manifest['smoke']]


def execute(index, manifest):
    folder = ROOT/'tasks'/f'{index:03d}'
    assert not folder.exists(), 'Partial branch requires diagnosis; no replay'
    (ROOT/'logs').mkdir(exist_ok=True)
    with (ROOT/'logs'/f'{index:03d}.log').open('x') as stream:
        subprocess.run([sys.executable,str(ROOT/'physics_worker.py'),str(index)],
            stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=BRANCH_TIMEOUT)
    expected = audit_result(read(folder/'result.json'),manifest['branches'][index],manifest)
    assert expected == read(folder/'summary.json')


def main(phase, shard):
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify()
    gate('gate_physics_smoke.json' if phase == 'batch' else 'gate_model.json')
    selected = indices(manifest,phase)[shard::SHARDS]
    path = ROOT/'stages'/phase/f'{shard}.json'
    assert not path.exists()
    status = dict(status='running',indices=selected,completed=0,expected=len(selected),
        job=os.environ['SLURM_JOB_ID'],started_at=time.time())
    save(path,status)
    try:
        for index in selected:
            execute(index,manifest)
            status['completed'] += 1
            save(path,status)
        status['status'] = 'completed'
    except BaseException as error:
        status.update(status='failed',error=repr(error))
        raise
    finally:
        status['ended_at'] = time.time()
        save(path,status)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase',choices=('smoke','batch'))
    parser.add_argument('--shard',type=int,choices=range(SHARDS),required=True)
    args = parser.parse_args()
    main(args.phase,args.shard)
