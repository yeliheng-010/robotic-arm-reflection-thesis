"""每个任务运行纯教师及同预算重试，保留中断目录。"""
import json
import os
from pathlib import Path
import sys
import numpy as np
from stability.experiment import BASE


def output_directory(root, arm):
    directory = Path(root)/arm
    completed = sorted(directory.glob('run_*/result.json'))
    if completed:
        if len(completed) != 1:
            raise RuntimeError('Multiple completed executions require audit')
        return completed[0].parent, json.loads(completed[0].read_text())
    number = len(list(directory.glob('run_*')))
    return directory/f'run_{number:03d}', None


def execute_arm(task, arm, root):
    from reflection.language import LABELS
    from stability.runtime import StableEngine
    from stability.teacher import AuditedTeacher
    directory, completed = output_directory(root, arm)
    if completed is not None:
        return directory, completed
    instruction = f"把{LABELS[task['source']]}放进{LABELS[task['destination']]}"
    teacher = AuditedTeacher(instruction, directory) if arm == 'teacher' else None
    class CollectionEngine(StableEngine):
        def _attempt(self, *args, **kwargs):
            record, report = super()._attempt(*args, **kwargs)
            record['candidate_trace']['source'] = 'geometric_proposals'
            count = len(record['candidate_trace'].get('returned', []))
            record['diagnostics']['available_candidate_count'] = count
            record['diagnostics']['selected_candidate_index'] = (
                min(record['parameters']['candidate_index'], count-1) if count else None)
            if report is not None:
                report.evidence['diagnostics'] = record['diagnostics']
                record['error'] = report.to_dict()
            return record, report

    engine = CollectionEngine(reflector=teacher, max_attempts=3, headless=True,
                          task_parser='rule', scene_jitter=.012)
    try:
        result = engine.run(**{k: v for k, v in task.items() if k != 'split'},
            instruction=instruction, method='reflection' if teacher else 'retry',
            output=directory, context='stable-collection')
        return directory, result
    finally:
        engine.close()


def verify_pair(teacher, retry):
    first, other = teacher['records'][0], retry['records'][0]
    for field in ('parameters', 'accepted', 'physical_success'):
        assert first[field] == other[field]
    assert (first['error'] or {}).get('error_type') == (other['error'] or {}).get('error_type')
    np.testing.assert_allclose(first['evaluation']['position'], other['evaluation']['position'], atol=1e-8, rtol=0)
    for field in ('initial_qpos', 'initial_body_xyz'):
        np.testing.assert_allclose(first['candidate_trace'][field], other['candidate_trace'][field], atol=1e-8, rtol=0)


def execute(task, root):
    os.chdir(BASE)
    sys.path.insert(0, str(BASE))
    from reflection.__main__ import bootstrap
    bootstrap()
    from stability.dataset import examples
    teacher_path, teacher = execute_arm(task, 'teacher', root)
    retry_path, retry = execute_arm(task, 'retry', root)
    verify_pair(teacher, retry)
    audit = teacher_path/'requests.jsonl'
    events = [json.loads(line) for line in audit.read_text().splitlines()] if audit.exists() else []
    rows = examples(teacher, retry, events, task_id=Path(root).name, split=task['split'])
    summary = {'task': task, 'teacher_success': teacher['success'], 'retry_success': retry['success'],
        'samples': rows, 'paired': True, 'teacher_result': str(teacher_path/'result.json'),
        'retry_result': str(retry_path/'result.json'),
        'invalid': sum('reflection_error' in r for r in teacher['records']),
        'calls': len(events), 'service_errors': sum('response' not in event for event in events)}
    target = Path(root)/'summary.json'
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    temporary.replace(target)
    return summary
