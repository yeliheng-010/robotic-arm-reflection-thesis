"""只替换相机，明确区分资格、真实结果与未知结果。"""
from copy import deepcopy


class VisibilityRejected(ValueError):
    pass


def adopt(case, config):
    if config is None:
        raise ValueError('Rejected camera cannot fall back to original')
    original = case['config']
    if case['item']['group'] == 'baseline' and config != original:
        raise ValueError('Baseline must remain unchanged')
    fields = lambda value: {k: v for k, v in value.items() if k != 'camera'}
    if fields(config) != fields(original):
        raise ValueError('Non-camera configuration changed')
    result = deepcopy(case)
    result['config'] = deepcopy(config)
    return result


def guarded_capture(check, capture):
    report = check()
    if report.get('accepted') is not True:
        raise VisibilityRejected('Observation rejected by visibility policy')
    return capture()


def paired_counts(rows):
    qualified = [r for r in rows if r['qualified']]
    pairs = [r for r in qualified if r.get('audit_passed') is True
             and type(r.get('new_success')) is bool and type(r.get('old_success')) is bool]
    return dict(registered=len(rows), qualified=len(qualified), audited_pairs=len(pairs),
        new_successes=sum(r['new_success'] for r in pairs),
        old_successes=sum(r['old_success'] for r in pairs),
        improved=sum(r['new_success'] and not r['old_success'] for r in pairs),
        regressed=sum(r['old_success'] and not r['new_success'] for r in pairs),
        unknown=len(qualified)-len(pairs), qualification_rejections=len(rows)-len(qualified))
