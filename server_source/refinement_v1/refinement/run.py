"""先 smoke 再开发回归；服务或审计失败中止，模型任务失败保留。"""
import argparse
import json
import os
import subprocess
import time
from stability.collection_status import atomic
from flashnext.client import ready
from flashnext.provenance import identity
from controlled.worker import jsonlines
from refinement.config import ROOT, SIM_PYTHON, WORKER_TIMEOUT, ARMS, runs, run_id
from refinement.freeze import verify


def execute(root, item):
    verify()
    if item['arm'].startswith('flash'):
        ready()
    command = [SIM_PYTHON, '-m', 'refinement.worker', '--mode', root.name]
    command += [x for key, value in item.items() for x in ('--'+key, str(value))]
    with (root/(run_id(item)+'.log')).open('x') as stream:
        subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=WORKER_TIMEOUT)
    directory = root/'tasks'/run_id(item)
    row = json.loads((directory/'summary.json').read_text())
    row['parsed_model_calls'] = sum('parsed' in e for e in jsonlines(directory/'requests.jsonl'))
    return row


def metrics(rows):
    output = {}
    for arm in ARMS:
        group = [r for r in rows if r['arm'] == arm]
        output[arm] = dict(runs=len(group), successes=sum(r['success'] for r in group),
                           invalid=sum(r['invalid_outputs'] for r in group),
                           exhausted=sum(r['policy_exhausted'] for r in group))
    return output


def gates(mode):
    verify()
    if mode == 'regression':
        smoke = json.loads((ROOT/'smoke/result.json').read_text())
        diagnostic = json.loads((ROOT/'diagnostic/result.json').read_text())
        assert smoke['status'] == diagnostic['status'] == 'completed'
        assert smoke['verification_passed'] and diagnostic['completed'] == 36
        for arm in ('flash_old', 'flash_new'):
            assert sum(r['parsed_model_calls'] for r in smoke['rows'] if r['arm'] == arm) > 0
    return ready()


def run(mode):
    models = gates(mode)
    root = ROOT/mode
    root.mkdir(exist_ok=False)
    order = runs(mode)
    atomic(root/'manifest.json', dict(models=models, identity=identity(), job=os.environ['SLURM_JOB_ID'],
                                    cuda_visible_devices=os.environ.get('CUDA_VISIBLE_DEVICES'), order=order))
    result = dict(status='running', expected=len(order), completed=0, rows=[], started_at=time.time(),
                  test_used=False, verification_passed=False)
    atomic(root/'progress.json', result)
    try:
        for item in order:
            row = execute(root, item)
            result['rows'].append(row)
            result['completed'] = len(result['rows'])
            atomic(root/'progress.json', result)
            print(json.dumps(row), flush=True)
            assert row['audit']['passed']
            if row['service_errors']:
                raise RuntimeError('Service failure; preserve full denominator and stop')
        verify()
        result.update(status='completed', verification_passed=True)
    except BaseException as error:
        result.update(status='failed', error=repr(error))
        raise
    finally:
        result.update(ended_at=time.time(), metrics=metrics(result['rows']))
        atomic(root/'result.json', result)
        atomic(root/'progress.json', result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('smoke', 'regression'), required=True)
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    run(parser.parse_args().mode)
