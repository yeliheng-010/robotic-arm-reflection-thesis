"""每个Slurm GPU步骤运行两条采集进程；仅写本分片任务。"""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import json
import os
from pathlib import Path
from stability.collection_status import atomic
from stability.experiment import THREADS
from stability.expert_config import configuration
from stability.recovery_task import execute_isolated
from stability.parallel_state import lane_indices, validate_plan, verify_identity, WORKERS_PER_GPU


def halted(root, control):
    return (root/'STOP').exists() or (control/'HALT.json').exists()


def run_lane(root, control, lane):
    deployment = verify_identity(root, control)
    config = json.loads((root/'manifest.json').read_text())
    assert config == configuration(config['stage'])
    total = deployment['task_limit'] or len(config['plan'])
    pending_indices = lane_indices(total, lane=lane, lanes=len(deployment['gpu_types']),
                                  completed=validate_plan(root, len(config['plan'])))
    state = {'lane': lane, 'job': os.environ.get('SLURM_JOB_ID'), 'pid': os.getpid(),
             'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES'), 'completed': [], 'errors': []}
    assert state['cuda_visible_devices'] and ',' not in state['cuda_visible_devices']
    target = control/f'lane_{lane}.json'
    atomic(target, state)
    iterator, pending = iter(pending_indices), {}
    with ThreadPoolExecutor(max_workers=WORKERS_PER_GPU) as pool:
        while True:
            while len(pending) < WORKERS_PER_GPU and not state['errors'] and not halted(root, control):
                index = next(iterator, None)
                if index is None:
                    break
                future = pool.submit(execute_isolated, config['plan'][index], str(root/'tasks'/f'{index:05d}'))
                pending[future] = index
            if not pending:
                break
            done, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                index = pending.pop(future)
                try:
                    result = future.result()
                    state['completed'].append(index)
                    print(json.dumps({'lane': lane, 'case': index, 'samples': len(result['samples'])}), flush=True)
                except Exception as error:
                    state['errors'].append({'case': index, 'error': repr(error)})
            atomic(target, state)
    state['finished'] = True
    atomic(target, state)
    if state['errors']:
        raise RuntimeError('Lane failure recorded')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--control', type=Path, required=True)
    parser.add_argument('--lane', type=int, required=True)
    args = parser.parse_args()
    assert all(os.environ.get(k) == v for k, v in THREADS.items())
    run_lane(args.root, args.control, args.lane)


if __name__ == '__main__':
    main()
