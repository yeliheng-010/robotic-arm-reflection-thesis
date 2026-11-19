"""冻结配置、有限并发、断点恢复和质量停机的批量采集入口。"""
import argparse
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import time
from stability.collection_plan import task_plan, FAULTS
from stability.collection_status import atomic, update
from stability.collection_worker import execute
from stability.experiment import OUT, THREADS, fingerprint
from stability.teacher import health
from stability.audit import validate_gate

FILES = ('teacher.py', 'prompt.py', 'dataset.py', 'collection_plan.py', 'collection_worker.py',
         'collection_status.py', 'collect.py', 'audit.py', 'teacher9_service.py')


def config(stage):
    hashes = {name: hashlib.sha256((OUT/'stability'/name).read_bytes()).hexdigest() for name in FILES}
    teacher = health()
    assert teacher['frozen'] and teacher['adapter'] is None and teacher['thinking'] is False
    return {'stage': stage, 'plan': task_plan(stage), 'code': fingerprint(),
            'collection_code': hashes, 'teacher': teacher, 'threads': THREADS,
            'workers': 2, 'max_attempts': 3, 'scene_jitter': .012,
            'source_boundary': 'Only actual LLM output; paired retry; persistent faults; no rule fallback'}


def stop_reason(status, *, stage):
    if status['sample_count_gate']:
        return 'sample_count_gate_met_pending_final_audit'
    if status['service_errors'] >= 2:
        return 'service_errors_require_review'
    if status['calls'] >= 20 and status['invalid']/status['calls'] > .2:
        return 'invalid_response_rate_above_20_percent'
    if stage == 'batch' and status['completed_tasks'] >= 120:
        counts = status['by_fault']['train']
        if any(counts.get(f, 0) == 0 for f in FAULTS):
            return 'persistent_fault_coverage_missing'
    return None


def run_pool(configuration, directory):
    plan = configuration['plan']
    remaining = iter((i, t) for i, t in enumerate(plan)
                     if not (directory/'tasks'/f'{i:05d}'/'summary.json').exists())
    status, pending, failures = update(directory, planned=len(plan)), {}, []
    reason = stop_reason(status, stage=configuration['stage'])
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
                    print(json.dumps({'case': index, 'success': result['teacher_success'],
                                      'samples': len(result['samples'])}), flush=True)
                except Exception as error:
                    failures.append({'case': index, 'error': repr(error)})
                    reason = 'worker_failure'
            status = update(directory, planned=len(plan))
            reason = reason or stop_reason(status, stage=configuration['stage'])
            if (directory/'STOP').exists():
                reason = 'user_stop_file'
    status['stop_reason'] = reason or 'plan_completed'
    status['ended'] = time.time()
    status['worker_failures'] = failures
    atomic(directory/'status.json', status)
    if failures:
        raise RuntimeError('Worker failures were saved; inspect status.json before resuming')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['pilot', 'batch'], required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    assert all(os.environ.get(k) == v for k, v in THREADS.items())
    configuration, directory = config(args.stage), OUT/args.run
    if args.stage == 'batch':
        validate_gate(json.loads((OUT/'pilot_gate.json').read_text()), configuration)
    manifest = directory/'manifest.json'
    if args.freeze:
        directory.mkdir(parents=True, exist_ok=True)
        with manifest.open('x') as stream:
            json.dump(configuration, stream, ensure_ascii=False, indent=2)
        return
    assert json.loads(manifest.read_text()) == configuration, 'Frozen collection config changed'
    atomic(directory/'runtime.json', {'slurm_job': os.environ.get('SLURM_JOB_ID'),
        'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES'), 'threads': THREADS})
    run_pool(configuration, directory)


if __name__ == '__main__':
    main()
