"""固定参数的单次完整物理干预；分片互不改写结果。"""
import argparse
import json
import os
import subprocess
import time
import numpy as np
from stability.collection_status import atomic
from refinement.config import SIM_PYTHON, WORKER_TIMEOUT
from nextstudy.protocol import ROOT, verify
from nextstudy.design import item_scenario

SHARDS = 2
PAIR_TOLERANCE = 1e-8


def engine_class(parameters):
    from reflection.__main__ import bootstrap
    bootstrap()
    from diversity.runtime import DiverseEngine
    from reflection.reflector import Parameters

    class DiagnosticEngine(DiverseEngine):
        def _attempt(self, *args, **kwargs):
            values = list(args)
            values[5] = Parameters().updated(parameters)
            return super()._attempt(*values, **kwargs)
    return DiagnosticEngine


def audit(result, item):
    record = result['records'][0]
    assert len(result['records']) == 1 and result['attempts'] == 1
    assert result['success'] == record['accepted']
    assert not record['accepted'] or record['physical_success']
    assert record['parameters'] == item['parameters']
    assert 'reflection' not in record and not result['llm_stats']
    trace = record['candidate_trace']
    count = len(trace.get('returned',[]))
    candidate_available = count > item['parameters']['candidate_index']
    if count:
        assert candidate_available, 'Unavailable candidate would be silently clamped'
    paired = item['case'] != 47 or all(item['factors'].values())
    if paired:
        path = ROOT.parent/'refinement_v3/regression/tasks'/f"{item['case']:02d}_flash_new_0/result.json"
        previous = json.loads(path.read_text())['records'][0]
        for field in ('initial_qpos','initial_body_xyz'):
            np.testing.assert_allclose(previous['candidate_trace'][field], trace[field],
                                       atol=PAIR_TOLERANCE, rtol=0)
    return dict(passed=True, parameters_executed=True, original_initial_state_paired=paired,
                diagnostic_intervention=True, model_calls=0, candidate_available=candidate_available)


def worker(index):
    protocol = verify()
    item = protocol['physical'][index]
    directory = ROOT/'physical/tasks'/item['id']
    assert not directory.exists(), 'Preserve prior run'
    config = item_scenario(item)
    engine = engine_class(item['parameters'])(scenario_config=config, max_attempts=1,
                                             headless=True, task_parser='rule')
    try:
        task = item['task']
        result = engine.run(**{k:task[k] for k in ('source','destination','fault','seed')},
                            output=directory, method='retry', context='diagnostic_intervention_v1')
    finally:
        engine.close()
    from controlled.feedback import project_report
    result = json.loads(json.dumps(result))
    record = result['records'][0]
    error = record.get('error') or {}
    projected = project_report(error, config, attempt=1) if error else None
    result.update(scenario=config, item=item, test_used=False, source='diagnostic_intervention',
                  projected_feedback=projected, training_approved=False)
    atomic(directory/'result.json', result)
    row = dict(id=item['id'], case=item['case'], factors=item['factors'], repeat=item['repeat'],
               success=result['success'], error=error.get('error_type'),
               diagnostics=record.get('diagnostics'), elapsed_s=result['elapsed_s'], audit=audit(result,item))
    atomic(directory/'summary.json', row)


def execute(item, index):
    directory = ROOT/'physical'
    saved = directory/'tasks'/item['id']
    if (saved/'summary.json').exists():
        result = json.loads((saved/'result.json').read_text())
        assert result['item'] == item and result['scenario'] == item_scenario(item)
        audit(result, item)
        row = json.loads((saved/'summary.json').read_text())
        assert row['success'] == result['success']
        return row
    with (directory/(item['id']+'.log')).open('x') as stream:
        subprocess.run([SIM_PYTHON, '-m', 'nextstudy.physical', '--index', str(index)],
                       stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=WORKER_TIMEOUT)
    return json.loads((directory/'tasks'/item['id']/'summary.json').read_text())


def run_shard(shard):
    protocol = verify()
    root = ROOT/'physical'
    root.mkdir(exist_ok=True)
    output = root/f'shard_{shard}'
    output.mkdir(exist_ok=False)
    order = [(i,r) for i,r in enumerate(protocol['physical']) if i % SHARDS == shard]
    result = dict(status='running', expected=len(order), completed=0, rows=[], started_at=time.time(),
                  job=os.environ['SLURM_JOB_ID'], cuda_visible_devices=os.getenv('CUDA_VISIBLE_DEVICES'))
    atomic(output/'progress.json', result)
    try:
        for index, item in order:
            verify()
            result['rows'].append(execute(item,index))
            result['completed'] = len(result['rows'])
            atomic(output/'progress.json', result)
        result['status'] = 'completed'
    except BaseException as error:
        result.update(status='failed', error=repr(error))
        raise
    finally:
        result['ended_at'] = time.time()
        atomic(output/'result.json', result)
        atomic(output/'progress.json', result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int)
    parser.add_argument('--shard', type=int, choices=range(SHARDS))
    args = parser.parse_args()
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    run_shard(args.shard) if args.index is None else worker(args.index)
