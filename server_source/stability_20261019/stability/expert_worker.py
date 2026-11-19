"""规则专家与同预算重试的物理配对；完整结果可恢复。"""
import json
import os
from pathlib import Path
import sys
from stability.collection_status import atomic
from stability.collection_worker import output_directory, execute_arm, verify_pair
from stability.experiment import BASE, execute as rule_execute
from stability.expert_dataset import examples, SOURCE


def summarize(task, root, *, expert_path, retry_path):
    expert = json.loads((expert_path/'result.json').read_text())
    retry = json.loads((retry_path/'result.json').read_text())
    verify_pair(expert, retry)
    assert expert['reflector'] == 'RuleReflector'
    assert all(r.get('reflection', {}).get('source', 'rule') == 'rule' for r in expert['records'])
    rows = examples(expert, retry, task_id=Path(root).name, split=task['split'])
    summary = {'task': task, 'supervision_source': SOURCE, 'samples': rows, 'paired': True,
        'expert_success': expert['success'], 'retry_success': retry['success'],
        'expert_result': str(expert_path/'result.json'), 'retry_result': str(retry_path/'result.json'),
        'invalid': sum('reflection_error' in r for r in expert['records']),
        'calls': sum('reflection' in r or 'reflection_error' in r for r in expert['records'])}
    atomic(Path(root)/'summary.json', summary)
    return summary


def execute(task, root):
    os.chdir(BASE)
    sys.path.insert(0, str(BASE))
    from reflection.__main__ import bootstrap
    bootstrap()
    expert_path, result = output_directory(root, 'expert')
    if result is None:
        rule_execute({k: v for k, v in task.items() if k != 'split'}, 'stable', str(expert_path))
    retry_path, _ = execute_arm(task, 'retry', root)
    return summarize(task, root, expert_path=expert_path, retry_path=retry_path)
