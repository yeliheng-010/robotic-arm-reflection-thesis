"""只替换首轮抓取策略；失败、退步和未知均保留。"""
from copy import deepcopy


def candidate(case):
    result = deepcopy(case)
    result['strategy'] = 'observed_top'
    validate_pair(case, result)
    return result


def validate_pair(original, proposed):
    if original['strategy'] != 'original' or proposed['strategy'] != 'observed_top':
        raise ValueError('Unexpected strategy comparison')
    if original['item']['group'] != 'varied_noisy':
        raise ValueError('Keep baseline unchanged')
    if original['state']['parameters']['grasp_offset'] != [0., 0., 0.]:
        raise ValueError('Cannot silently clear an existing offset')
    without_strategy = lambda value: {k: v for k, v in value.items() if k != 'strategy'}
    if without_strategy(original) != without_strategy(proposed):
        raise ValueError('Only strategy may change')
    return True


def summarize(rows, registered):
    seeds = [r['seed'] for r in rows]
    if len(set(registered)) != len(registered) or len(set(seeds)) != len(seeds):
        raise ValueError('Duplicate condition')
    if not set(seeds).issubset(set(registered)):
        raise ValueError('Foreign condition')
    pairs = [r for r in rows if r.get('audit_passed') is True
             and type(r.get('new_success')) is bool and type(r.get('old_success')) is bool]
    return dict(registered=len(registered), audited_pairs=len(pairs), unknown=len(registered)-len(pairs),
        new_successes=sum(r['new_success'] for r in pairs),
        old_successes=sum(r['old_success'] for r in pairs),
        improved=sum(r['new_success'] and not r['old_success'] for r in pairs),
        regressed=sum(r['old_success'] and not r['new_success'] for r in pairs))
