"""只能在观测拟合和选择落盘后读取私有真值。"""
from visibility_calibration_v1.analysis import accuracy
from pose_fresh_v1.common import read, save, sha

STRATEGIES = ('original', 'repaired', 'selective')


def annotate(fitted, views, truth):
    qualified = {v['index']: v.get('full_frame_qualified', False) for v in views}
    result = {}
    for kind in ('singles', 'pairs'):
        result[kind] = []
        for row in fitted[kind]:
            indices = row.get('indices', [row.get('index')])
            values = {name: dict(accuracy(row[name]['fit'], truth),
                                accepted=row[name]['quality_passed'])
                      for name in ('original', 'repaired')}
            values['selective'] = (dict(values[row['choice']]) if row['choice']
                                   else dict(accuracy(None, truth), accepted=False))
            result[kind].append(dict(indices=indices, repeat=row['repeat'],
                full_frame_qualified=all(qualified[i] for i in indices),
                choice=row['choice'], **values))
    return result


def count(rows):
    report = {}
    for name in STRATEGIES:
        values = [r[name] for r in rows]
        report[name] = dict(observations=len(values),
            accurate=sum(v['accurate'] for v in values),
            accepted=sum(v['accepted'] for v in values),
            accepted_accurate=sum(v['accepted'] and v['accurate'] for v in values),
            false_accepted=sum(v['accepted'] and not v['accurate'] for v in values))
    report['repair_new_false_accepts'] = sum(r['choice'] == 'repaired'
        and not r['selective']['accurate'] for r in rows)
    report['original_accepted_losses'] = sum(r['original']['accepted']
        and (r['choice'] != 'original' or r['selective'] != r['original']) for r in rows)
    return report


def summarize(errors):
    return {kind: {group: count([r for r in rows if group == 'all_calibrated'
                  or r['full_frame_qualified'] == (group == 'qualified')])
                  for group in ('all_calibrated', 'qualified', 'private_diagnostic')}
            for kind, rows in errors.items()}


def run(folder):
    fitted = read(folder / 'fits.json')
    digest = sha(folder / 'fits.json')
    truth = read(folder / 'private_truth.json')
    errors = annotate(fitted, read(folder / 'views.json'), truth)
    save(folder / 'private_errors.json', errors)
    return dict(fits_before_evaluation_sha256=digest, metrics=summarize(errors))
