"""专家采集独立身份；复用已经验证的物理版本与任务切分。"""
import hashlib
from stability.collection_plan import task_plan
from stability.experiment import OUT, THREADS, fingerprint
from stability.expert_dataset import SOURCE

FILES = ('expert_dataset.py', 'expert_worker.py', 'expert_status.py', 'expert_config.py',
         'expert_collect.py', 'expert_audit.py', 'expert_pilot.py',
         'collection_plan.py', 'collection_worker.py', 'collection_status.py',
         'teacher.py', 'dataset.py', 'prompt.py')


def configuration(stage):
    return {'stage': stage, 'plan': task_plan(stage), 'code': fingerprint(),
        'expert_code': {name: hashlib.sha256((OUT/'stability'/name).read_bytes()).hexdigest() for name in FILES},
        'supervision_source': SOURCE, 'generator': 'reflection.reflector.RuleReflector',
        'model': None, 'threads': THREADS, 'workers': 2, 'max_attempts': 3, 'scene_jitter': .012,
        'source_boundary': 'Programmatic rule expert; replayed labels; paired retry; no LLM attribution'}


def validate_gate(gate, config):
    assert gate['allow_batch'], 'Expert pilot gate failed'
    for key in ('code', 'expert_code', 'supervision_source', 'generator'):
        assert gate[key] == config[key], 'Expert pilot identity mismatch: '+key
