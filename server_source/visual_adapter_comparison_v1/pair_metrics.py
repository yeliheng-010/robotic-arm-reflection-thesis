"""同输入配对描述统计；未知动作不推定成功或失败。"""
from collections import Counter

BAD = {'invalid_output', 'stop_before_completion', 'observed_failure'}
SUCCESS = 'observed_success'
CATEGORIES = BAD | {SUCCESS, 'completed_stop', 'unmeasured_action', 'mixed_observed_outcomes'}


def summarize(rows):
    return dict(inputs=len(rows), seed_groups=len({r['seed'] for r in rows}),
        base=dict(Counter(r['base'] for r in rows)),
        tuned=dict(Counter(r['tuned'] for r in rows)),
        transitions=dict(Counter(r['base']+' -> '+r['tuned'] for r in rows)),
        verified_improvements=sum(r['base'] in BAD and r['tuned'] == SUCCESS for r in rows),
        verified_regressions=sum(r['base'] == SUCCESS and r['tuned'] in BAD for r in rows))


def compare_pairs(base, tuned, *, seeds):
    old = {r['input_id']: r for r in base}
    new = {r['input_id']: r for r in tuned}
    assert len(old) == len(base) and len(new) == len(tuned)
    assert set(old) == set(new) == set(seeds)
    pairs = []
    for key, first in old.items():
        last = new[key]
        assert first['snapshot_id'] == last['snapshot_id']
        assert first['completed'] is last['completed']
        assert first['model'] in CATEGORIES and last['model'] in CATEGORIES
        pairs.append(dict(input_id=key, snapshot_id=first['snapshot_id'], seed=seeds[key],
            completed=first['completed'], base=first['model'], tuned=last['model']))
    return dict(natural=summarize([r for r in pairs if not r['completed']]),
        completed=summarize([r for r in pairs if r['completed']]), pairs=pairs,
        limitation='Offline measured-option agreement is not physical recovery performance')
