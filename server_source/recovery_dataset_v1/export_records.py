import hashlib
import json
from copy import deepcopy
from check_input import public
from sv_strategy_actions import check
from f_common import read, sha


def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',',':'))


def outcome(request, row, *, stop):
    facts = [r['value'] for r in request['evidence'] if r['field']=='execution_facts']
    assert len(facts)==1 and facts[0]['task_completed'] is stop
    if stop:
        assert row['action'] == dict(id='STOP',args={})
    else:
        assert row['before']['success'] is False and row['successor']['success'] is True
        assert row['successor']['index'] == row['before']['index']+1
        assert row['action']['id'] not in ('OBSERVE','STOP')


def record(row, *, stop=False):
    assert stop or row['eligible_natural'] and row['verified_recovery']
    assert sha(row['input_path']) == row['input_sha256']
    bundle = read(row['input_path'])
    public(bundle['request'])
    outcome(bundle['request'],row,stop=stop)
    check(row['action'], bundle['request'])
    assert all(sha(p) == h for p,h in zip(bundle['visual']['paths'], bundle['visual']['sha256']))
    messages = deepcopy(bundle['direct_messages'])
    assert [r['role'] for r in messages] == ['system','user']
    assert json.loads(messages[1]['content']) == bundle['request']
    key = hashlib.sha256(canonical(dict(messages=messages, images=bundle['visual']['sha256'])).encode()).hexdigest()
    content = [dict(type='image', image=p) for p in bundle['visual']['paths']]
    content.append(dict(type='text', text=messages[1]['content']))
    messages[1]['content'] = content
    messages.append(dict(role='assistant', content=canonical(dict(action=row['action']))))
    return dict(input_id=key, snapshot_id=row['snapshot_id'], seed=row['seed'], split=row['split'],
        source_input=row['input_path'], source_sha256=row['input_sha256'], messages=messages,
        action=row['action'], kind='completed_stop' if stop else 'verified_recovery',
        image_sha256=bundle['visual']['sha256'], label_scope='one_verified_option_not_unique_optimum')


def deduplicate(rows):
    groups = {}
    for row in rows:
        group = groups.setdefault(row['input_id'], [])
        assert not group or all(row[k] == group[0][k] for k in ('split','snapshot_id'))
        group.append(row)
    selected = []
    for key, group in sorted(groups.items()):
        choices = {canonical(r['action']):r for r in group}
        value = deepcopy(choices[min(choices)])
        value['accepted_actions'] = [choices[k]['action'] for k in sorted(choices)]
        selected.append(value)
    return selected


def select_training(rows):
    positive = [r for r in rows if r['kind']=='verified_recovery']
    stops = [r for r in rows if r['kind']=='completed_stop']
    distinct_stops = {r['snapshot_id']:r for r in sorted(stops, key=lambda x:x['input_id'])}
    cap = len({r['snapshot_id'] for r in positive})//2
    return positive+list(distinct_stops.values())[:cap]
