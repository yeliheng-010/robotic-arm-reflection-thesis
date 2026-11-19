"""带独占锁、冻结校验、断点恢复和质量停机的专家批量采集。"""
import argparse
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
import fcntl
import json
import multiprocessing
import os
import time
from stability.collection_plan import FAULTS
from stability.collection_status import atomic
from stability.experiment import OUT, THREADS
from stability.expert_config import configuration, validate_gate
from stability.expert_status import update
from stability.expert_worker import execute


def stop_reason(status, directory):
    if (directory/'STOP').exists():
        return 'user_stop_file'
    if status['sample_count_gate']:
        return 'sample_count_gate_met_pending_final_audit'
    if status['calls'] >= 20 and status['invalid']/status['calls'] > .2:
        return 'invalid_rule_rate_above_20_percent'
    if status['completed_tasks'] >= 120:
        if any(status['by_fault']['train'].get(f, 0) == 0 for f in FAULTS):
            return 'persistent_fault_coverage_missing'
    return None


def run_pool(config, directory):
    plan = config['plan']
    remaining = iter((i, t) for i, t in enumerate(plan)
                     if not (directory/'tasks'/f'{i:05d}'/'summary.json').exists())
    status = update(directory, planned=len(plan), stage=config['stage'])
    pending, failures, reason = {}, [], stop_reason(status, directory)
    with ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context('spawn')) as pool:
        while True:
            while len(pending) < 2 and reason is None:
                item = next(remaining, None)
                if item is None:
                    break
                index, task = item
                pending[pool.submit(execute, task, str(directory/'tasks'/f'{index:05d}'))] = index
            if not pending:
                break
            done, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                index = pending.pop(future)
                try:
                    result = future.result()
                    print(json.dumps({'case': index, 'expert_success': result['expert_success'],
                                      'samples': len(result['samples'])}), flush=True)
                except Exception as error:
                    failures.append({'case': index, 'error': repr(error)})
                    reason = 'worker_failure'
            status = update(directory, planned=len(plan), stage=config['stage'])
            reason = reason or stop_reason(status, directory)
            try:
                assert configuration(config['stage']) == config, 'Frozen configuration changed'
            except Exception as error:
                failures.append({'error': repr(error)})
                reason = 'configuration_drift'
    status.update(stop_reason=reason or 'plan_completed', ended=time.time(), worker_failures=failures)
    atomic(directory/'status.json', status)
    if failures:
        raise RuntimeError('Failures saved in status.json; review before resuming')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['pilot', 'batch'], required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    assert all(os.environ.get(k) == v for k, v in THREADS.items())
    assert args.run.startswith('expert_') and '/' not in args.run
    config, directory = configuration(args.stage), OUT/args.run
    if args.stage == 'batch':
        validate_gate(json.loads((OUT/'expert_gate.json').read_text()), config)
    manifest = directory/'manifest.json'
    if args.freeze:
        directory.mkdir(exist_ok=True)
        with manifest.open('x') as stream:
            json.dump(config, stream, ensure_ascii=False, indent=2)
        return
    assert json.loads(manifest.read_text()) == config
    with (directory/'.collector.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        atomic(directory/'runtime.json', {'job': os.environ.get('SLURM_JOB_ID'),
            'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES'), 'threads': THREADS})
        run_pool(config, directory)


if __name__ == '__main__':
    main()
