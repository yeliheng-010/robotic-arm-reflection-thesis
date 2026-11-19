"""配对统计保留所有拒绝、校验退化与无射线参考。"""
from sensor_independent_v1.common import METHODS


def transitions(pairs):
    return dict(total=len(pairs), original_pass=sum(a for a, b in pairs),
        no_msaa_pass=sum(b for a, b in pairs), gained=sum(not a and b for a, b in pairs),
        lost=sum(a and not b for a, b in pairs))


def paired_counts(rows):
    measured = [r for r in rows if 'methods' in r]
    return dict(candidates=len(rows), measured=len(measured),
        qualification=transitions([(r['methods']['original']['accepted'], r['methods']['no_msaa']['accepted']) for r in measured]),
        calibration=transitions([(r['methods']['original']['calibration']['passed'], r['methods']['no_msaa']['calibration']['passed']) for r in measured]),
        fixed_old_mask=transitions([(r['methods']['original']['calibration']['passed'], r['fixed_old_mask']['passed']) for r in measured]))


def ray_metrics(rows):
    valid = [r for r in rows if r['ray_depth_m'] is not None]
    result = dict(references=len(rows), valid=len(valid), missing=len(rows)-len(valid))
    for method in METHODS:
        errors = [abs(r[method]['depth_m'] - r['ray_depth_m']) for r in valid]
        result[method] = dict(mae_m=sum(errors)/len(errors) if errors else None,
            maximum_m=max(errors) if errors else None,
            errors_over_1mm=sum(e > .001 for e in errors),
            root_mismatches=sum(r[method]['root'] != r['ray_root'] for r in valid))
    return result


def ray_nonregression(result):
    if result['valid'] == 0:
        return False
    old, new = result['original'], result['no_msaa']
    return new['mae_m'] <= old['mae_m'] + 1e-6 and new['root_mismatches'] <= old['root_mismatches']
