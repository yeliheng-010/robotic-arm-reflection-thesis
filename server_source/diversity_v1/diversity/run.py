"""先通过预检，再冻结代码和场景；独立输出逐步进度。"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from stability.collection_status import atomic
from stability.experiment import fingerprint
from diversity.config import pilot_tasks, scenario, task_matrix
from diversity.worker import ROOT, ARMS
from diversity.audit import audit_case, summarize
from flashnext.client import ready
from flashnext.provenance import identity
from diversity.report import write_report

SIM_PYTHON = '/home/yeliheng/grasp_server/env_sim/bin/python'


def source_hashes():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}


def execute(case, arm):
    with (ROOT/f'task_{case:02d}_{arm}.log').open('x') as stream:
        subprocess.run([SIM_PYTHON, '-m', 'diversity.worker', '--case', str(case), '--arm', arm],
                       stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=1800)
    return json.loads((ROOT/'tasks'/f'{case:02d}'/arm/'summary.json').read_text())


def initialize():
    preflight = json.loads((ROOT.parent/'preflight/result.json').read_text())
    assert preflight['passed'] and preflight['cases'] == 16
    for task, row in zip(pilot_tasks(), preflight['rows']):
        assert task == row['task'] and scenario(task['seed'], task['level']) == row['scenario']
    ROOT.mkdir(exist_ok=False)
    frozen = source_hashes()
    manifest = dict(code=frozen, physics=fingerprint(), model=identity(), models=ready(),
                    tasks=pilot_tasks(), arms=ARMS, max_attempts=3, max_tokens=1024,
                    test_used=False, job=os.environ['SLURM_JOB_ID'],
                    cuda_visible_devices=os.environ.get('CUDA_VISIBLE_DEVICES'))
    atomic(ROOT/'manifest.json', manifest)
    atomic(ROOT.parent/'candidate_matrix.json', {'tasks': task_matrix(seeds_per_group=2),
                                                'status': 'planned_not_executed', 'test_used': False})
    return frozen


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm for simulation'
    frozen = initialize()
    rows, audits = [], []
    result = dict(status='running', started_at=time.time(), expected_tasks=32, test_used=False)
    try:
        for case, task in enumerate(pilot_tasks()):
            for arm in ARMS:
                assert frozen == source_hashes(), 'Code changed during pilot'
                rows.append(execute(case, arm))
                result.update(completed=len(rows), rows=rows, metrics=summarize(rows))
                atomic(ROOT/'progress.json', result)
                print(json.dumps(rows[-1]), flush=True)
            audits.append(audit_case(case, task))
            atomic(ROOT/'audits.json', audits)
        result.update(status='completed', audits=audits, verification_passed=True)
        write_report(ROOT, result)
    except BaseException as error:
        result.update(status='failed', error=repr(error))
        raise
    finally:
        result['ended_at'] = time.time()
        atomic(ROOT/'result.json', result)


if __name__ == '__main__':
    main()

