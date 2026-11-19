"""通过 Slurm 使用一张仿真卡；推理复用管理员管理的共享服务。"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from stability.collection_status import atomic
from stability.loop_protocol import plan
from stability.experiment import fingerprint
from flashnext.worker import ROOT, ARMS
from flashnext.audit import audit_case, summarize
from flashnext.client import ready
from flashnext.provenance import identity

SIM_PYTHON = '/home/yeliheng/grasp_server/env_sim/bin/python'


def code_identity():
    package = Path(__file__).parent
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(package.glob('*.py'))}


def execute(case, arm):
    with (ROOT/f'task_{case:02d}_{arm}.log').open('x') as stream:
        subprocess.run([SIM_PYTHON, '-m', 'flashnext.worker', '--case', str(case), '--arm', arm],
                       stdout=stream, stderr=subprocess.STDOUT, timeout=1800, check=True)
    path = ROOT/'tasks'/f'{case:02d}'/arm/'summary.json'
    return json.loads(path.read_text())


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Simulation requires Slurm allocation'
    ROOT.mkdir(exist_ok=False)
    frozen = code_identity()
    manifest = dict(tasks=plan(), arms=ARMS, code=frozen, physics=fingerprint(),
                    max_attempts=3, scene_jitter=.012, max_tokens=1024, test_used=False,
                    job=os.environ['SLURM_JOB_ID'], models=ready(), provenance=identity(),
                    cuda_visible_devices=os.environ.get('CUDA_VISIBLE_DEVICES'))
    atomic(ROOT/'manifest.json', manifest)
    rows, audits = [], []
    result = dict(status='running', started_at=time.time(), expected_tasks=18,
                  test_used=False, scope='six development scenes, not final test')
    try:
        for case, task in enumerate(plan()):
            for arm in ARMS:
                assert code_identity() == frozen, 'Source changed during execution'
                rows.append(execute(case, arm))
                result.update(completed=len(rows), metrics=summarize(rows), rows=rows)
                atomic(ROOT/'progress.json', result)
                print(json.dumps(rows[-1]), flush=True)
            audits.append(audit_case(case, task))
            atomic(ROOT/'audits.json', audits)
        result.update(status='completed', audits=audits)
    except BaseException as error:
        result.update(status='failed', error=repr(error))
        raise
    finally:
        result['ended_at'] = time.time()
        atomic(ROOT/'result.json', result)


if __name__ == '__main__':
    main()
