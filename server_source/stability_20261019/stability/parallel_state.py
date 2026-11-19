"""多GPU任务分片与冻结的独立调度身份。"""
import hashlib
import json
from pathlib import Path

FILES = ('parallel_state.py', 'parallel_lane.py', 'parallel_collect.py',
         'recovery_task.py', 'recovery_audit.py', 'recovery_review.py')
WORKERS_PER_GPU = 2
LANE_MEMORY = '24G'


def lane_indices(total, *, lane, lanes, completed):
    if lanes <= 0 or not 0 <= lane < lanes:
        raise ValueError('Invalid lane assignment')
    return [i for i in range(lane, total, lanes) if i not in completed]


def topology(gpus):
    if gpus == 1:
        return ['v100']
    if gpus not in (2, 4):
        raise ValueError('Only one/two/four GPU topologies are supported')
    return ['v100', 'v100'] if gpus == 2 else ['svc', 'svc', 'v100', 'v100']


def validate_plan(root, total):
    completed = set()
    for path in (root/'tasks').glob('*/summary.json'):
        name = path.parent.name
        if not name.isdigit() or name != f'{int(name):05d}' or not 0 <= int(name) < total:
            raise ValueError('Unexpected task directory: '+name)
        completed.add(int(name))
    return completed


def identity(root, *, gpus, limit):
    code = Path(__file__).parent
    return {'manifest_sha256': hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest(),
        'scheduler_code': {n: hashlib.sha256((code/n).read_bytes()).hexdigest() for n in FILES},
        'gpu_types': topology(gpus), 'workers_per_gpu': WORKERS_PER_GPU,
        'task_limit': limit, 'partition_rule': 'original_task_index_modulo_gpu_count',
        'lane_memory': LANE_MEMORY, 'process_policy': 'one_task_per_fresh_interpreter',
        'base_workers_meaning': 'Frozen single-lane baseline; each GPU lane retains two workers'}


def verify_identity(root, control):
    frozen = json.loads((control/'manifest.json').read_text())
    assert frozen == identity(root, gpus=len(frozen['gpu_types']), limit=frozen['task_limit'])
    return frozen
