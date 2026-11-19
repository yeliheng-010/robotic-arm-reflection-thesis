"""持有唯一批次锁的多GPU调度器；统一统计、停止与最终审计。"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from stability.collection_status import atomic
from stability.experiment import OUT, THREADS
from stability.recovery_audit import audit
from stability.recovery_review import check_admission
from stability.expert_collect import stop_reason
from stability.expert_config import configuration, validate_gate
from stability.expert_status import update
from stability.parallel_state import identity, verify_identity, validate_plan, LANE_MEMORY

POLL_SECONDS = 5


def launch(root, control, deployment):
    processes = []
    for lane, gpu_type in enumerate(deployment['gpu_types']):
        command = ['srun', '--exclusive', '--exact', '--nodes=1', '--ntasks=1',
                   '--cpus-per-task=8', '--mem='+LANE_MEMORY, '--gres=gpu:'+gpu_type+':1',
                   '--cpu-bind=cores', '--output='+str(control/f'lane_{lane}.log'),
                   sys.executable, '-m', 'stability.parallel_lane', '--root', str(root),
                   '--control', str(control), '--lane', str(lane)]
        processes.append(subprocess.Popen(command))
    return processes


def monitor(root, control, *, config, processes):
    reason, failures = None, []
    while True:
        try:
            verify_identity(root, control)
            assert config == configuration(config['stage']), 'Base code drift'
            status = update(root, planned=len(config['plan']), stage=config['stage'])
            reason = reason or stop_reason(status, root)
        except Exception as error:
            failures.append({'error': repr(error)})
            reason = 'configuration_or_status_failure'
        codes = [p.poll() for p in processes]
        if any(code not in (None, 0) for code in codes):
            reason = reason or 'lane_failure'
        if (control/'HALT.json').exists():
            reason = reason or json.loads((control/'HALT.json').read_text())['reason']
        if reason and not (control/'HALT.json').exists():
            atomic(control/'HALT.json', {'reason': reason})
        if all(code is not None for code in codes):
            break
        time.sleep(POLL_SECONDS)
    failures.extend({'lane': i, 'exit_code': c} for i, c in enumerate(codes) if c != 0)
    status = update(root, planned=len(config['plan']), stage=config['stage'])
    status.update(stop_reason=reason or 'assigned_tasks_completed', ended=time.time(), worker_failures=failures,
                  orchestration=str(control), job=os.environ.get('SLURM_JOB_ID'))
    atomic(root/'status.json', status)
    atomic(control/'result.json', {'status': status, 'lane_exit_codes': codes})
    if failures:
        raise RuntimeError('Parallel failures require review')
    return audit(root)


def run(root, control, config):
    with (root/'.collector.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not (root/'STOP').exists(), 'Resolve prior stop before resuming'
        assert not (control/'HALT.json').exists(), 'Use a new reviewed deployment after a halt'
        deployment = verify_identity(root, control)
        validate_plan(root, len(config['plan']))
        old_status = json.loads((root/'status.json').read_text()) if (root/'status.json').exists() else {}
        recovery = check_admission(root, control, old_status)
        audit(root)
        atomic(control/'runtime.json', {'job': os.environ.get('SLURM_JOB_ID'),
            'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES'), 'threads': THREADS,
            'gpu_types': deployment['gpu_types'], 'workers_per_gpu': 2, 'recovery_record': recovery})
        processes = launch(root, control, deployment)
        result = monitor(root, control, config=config, processes=processes)
        print(json.dumps({'source_audit_passed': result['source_audit_passed'],
                          'audited_tasks': result['audited_tasks']}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--deployment', required=True)
    parser.add_argument('--gpus', type=int, choices=[1, 2, 4], required=True)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    assert all('/' not in value and value.startswith('expert_') for value in (args.run, args.deployment))
    assert all(os.environ.get(k) == v for k, v in THREADS.items())
    root, control = OUT/args.run, OUT/args.deployment
    config = json.loads((root/'manifest.json').read_text())
    assert config == configuration(config['stage'])
    validate_gate(json.loads((OUT/'expert_gate.json').read_text()), config)
    assert 0 <= args.limit <= len(config['plan'])
    deployment = identity(root, gpus=args.gpus, limit=args.limit)
    if args.freeze:
        control.mkdir(exist_ok=False)
        atomic(control/'manifest.json', deployment)
        return
    assert json.loads((control/'manifest.json').read_text()) == deployment
    run(root, control, config)


if __name__ == '__main__':
    main()
