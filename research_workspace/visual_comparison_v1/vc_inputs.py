"""公开输入独立文件，私有已测后果独立文件。"""
import hashlib
import json
from check_input import public
from f_common import read, sha
from vc_metrics import canonical


def build(path, expected):
    assert sha(path) == expected
    bundle = read(path)
    public(bundle['request'])
    messages = bundle['direct_messages']
    assert [m['role'] for m in messages] == ['system', 'user']
    assert json.loads(messages[1]['content']) == bundle['request']
    visual = bundle['visual']
    assert len(visual['paths']) == len(visual['sha256']) == 2
    assert all(sha(p) == h for p, h in zip(visual['paths'], visual['sha256']))
    key = hashlib.sha256(canonical(dict(messages=messages, images=visual['sha256'])).encode()).hexdigest()
    return dict(input_id=key, request=bundle['request'], messages=messages,
        images=visual['paths'], image_sha256=visual['sha256'])


def collect(rows, stops):
    inputs, private = {}, {}
    for row in rows:
        if row['split'] != 'dev' or not row['eligible_natural']:
            continue
        value = build(row['input_path'], row['input_sha256'])
        key = value['input_id']
        inputs.setdefault(key, value)
        facts = private.setdefault(key, dict(input_id=key, snapshot_id=row['snapshot_id'],
            seed=row['seed'], completed=False, outcomes=[]))
        assert facts['snapshot_id'] == row['snapshot_id'] and facts['seed'] == row['seed']
        facts['outcomes'].append(dict(action=row['action'], success=row['successor']['success']))
    for row in stops:
        if row['kind'] != 'completed_stop':
            continue
        assert row['split'] == 'dev'
        value = build(row['source_input'], row['source_sha256'])
        key = value['input_id']
        assert key not in private
        facts = [e['value'] for e in value['request']['evidence'] if e['field'] == 'execution_facts']
        assert len(facts) == 1 and facts[0]['task_completed'] is True
        inputs[key] = value
        private[key] = dict(input_id=key, snapshot_id=row['snapshot_id'], seed=row['seed'],
            completed=True, outcomes=[])
    assert inputs
    return [inputs[k] for k in sorted(inputs)], [private[k] for k in sorted(private)]
