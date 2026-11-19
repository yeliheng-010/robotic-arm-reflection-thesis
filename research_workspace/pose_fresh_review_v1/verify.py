"""不导入被审算法，独立重算全部误差、接受门槛及策略统计。"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'pose_fresh_v1/evidence/remote/run'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def accuracy(fit, truth):
    if fit is None:
        return dict(accurate=False, center_error_m=None, axis_error_deg=None)
    center = math.dist(fit['center'], truth['center'])
    dot = abs(sum(a*b for a, b in zip(fit['axis'], truth['axis'])))
    angle = math.degrees(math.acos(min(1., max(0., dot))))
    return dict(accurate=center <= .010 and angle <= 12., center_error_m=center, axis_error_deg=angle)


def quality(fit):
    return bool(fit is not None and fit['converged'] and fit['p95_m'] <= .006
                and fit['condition'] < 1e4 and fit['half_length'] >= fit['radius'])


def consistent(fits):
    from itertools import combinations
    if not all(quality(f) for f in fits):
        return False
    for one, two in combinations(fits, 2):
        if math.dist(one['center'], two['center']) > .010:
            return False
        dot = abs(sum(a*b for a, b in zip(one['axis'], two['axis'])))
        if math.degrees(math.acos(min(1., max(0., dot)))) > 12.:
            return False
    return True


def check_row(row, errors, *, kind, cache, truth):
    choice = 'original' if row['original']['quality_passed'] else (
        'repaired' if row['repaired']['quality_passed'] else None)
    assert row['choice'] == errors['choice'] == choice
    for name in ('original', 'repaired'):
        fit = row[name]['fit']
        expected = accuracy(fit, truth)
        for key, value in expected.items():
            actual = errors[name][key]
            assert actual == value if value is None or type(value) is bool else math.isclose(actual, value, abs_tol=1e-10)
        accepted = quality(fit) if kind == 'singles' else consistent(
            [fit, *[cache[i, row['repeat']][name]['fit'] for i in row['indices']]])
        assert accepted == row[name]['quality_passed'] == errors[name]['accepted']
    selected = errors[choice] if choice else dict(accuracy(None, truth), accepted=False)
    assert errors['selective'] == selected


def counts(rows):
    result = {}
    for strategy in ('original', 'repaired', 'selective'):
        accepted = [r[strategy] for r in rows if r[strategy]['accepted']]
        result[strategy] = dict(observations=len(rows), accurate=sum(r[strategy]['accurate'] for r in rows),
            accepted=len(accepted), accepted_accurate=sum(r['accurate'] for r in accepted),
            false_accepted=sum(not r['accurate'] for r in accepted))
    result['repair_new_false_accepts'] = sum(r['choice'] == 'repaired' and not r['selective']['accurate'] for r in rows)
    result['original_accepted_losses'] = sum(r['original']['accepted'] and r['choice'] != 'original' for r in rows)
    return result


def summary(errors):
    return {kind: {group: counts([r for r in rows if group == 'all_calibrated'
                    or r['full_frame_qualified'] == (group == 'qualified')])
                  for group in ('all_calibrated', 'qualified', 'private_diagnostic')}
            for kind, rows in errors.items()}


def layout(folder, result):
    fitted, errors = read(folder / 'fits.json'), read(folder / 'private_errors.json')
    truth, views = read(folder / 'private_truth.json'), read(folder / 'views.json')
    full = {v['index']: v['full_frame_qualified'] for v in views}
    cache = {(r['index'], r['repeat']): r for r in fitted['singles']}
    for kind, rows in errors.items():
        assert len(rows) == len(fitted[kind])
        for row, error in zip(fitted[kind], rows):
            check_row(row, error, kind=kind, cache=cache, truth=truth)
            assert error['full_frame_qualified'] == all(full[i] for i in error['indices'])
    assert summary(errors) == result['metrics']
    return errors


def main():
    audit = read(SOURCE / 'audit.json')
    combined, digests = dict(singles=[], pairs=[]), {}
    for seed, result in audit['layouts'].items():
        folder = SOURCE / seed
        for name, digest in result['evidence'].items():
            if name.endswith('.json'):
                assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest
                digests[f'{seed}/{name}'] = digest
        if result['qualified']:
            for kind, rows in layout(folder, result).items():
                combined[kind].extend(rows)
    assert summary(combined) == audit['metrics']
    result = dict(passed=True, independent_implementation=True, text_hashes=len(digests),
        singles=len(combined['singles']), pairs=len(combined['pairs']),
        selected_repair_count=sum(r['choice'] == 'repaired' for rows in combined.values() for r in rows),
        metrics=summary(combined), source_audit_sha256=hashlib.sha256((SOURCE / 'audit.json').read_bytes()).hexdigest())
    (ROOT / 'verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print({k: v for k, v in result.items() if k != 'metrics'})


if __name__ == '__main__':
    main()
