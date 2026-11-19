"""本地只读重算已归档数值和统计，不启动仿真或重拟合。"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REMOTE = ROOT / 'evidence/remote'
RUN = REMOTE / 'run'
METHODS = ('original', 'no_msaa')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_rows(folder, recorded):
    rows = read(folder / 'observations.json')
    assert rows == [json.loads(s) for s in (folder / 'observations.jsonl').read_text().splitlines()]
    measured = [r for r in rows if 'methods' in r]
    rgb_failures = sum(not r['rgb']['passed'] for r in measured)
    assert rgb_failures == recorded['rgb_failures']
    for row in measured:
        rgb = row['rgb']
        assert rgb['passed'] == (rgb['max_channel_delta'] <= 2 and rgb['changed_fraction'] <= .001)
        assert rgb['changed_fraction'] == rgb['changed_pixels'] / (rgb['shape'][0] * rgb['shape'][1])
        for method in METHODS:
            value = row['methods'][method]
            assert value['geometry_accepted'] == (value['gate']['passed'] and value['calibration']['passed'])
            assert value['accepted'] == (value['geometry_accepted'] and rgb['passed'])
    best = min(measured, key=lambda r: (len(r['methods']['no_msaa']['gate']['rejected']), r['index']))
    bottlenecks = {k: v['reasons'] for k, v in best['methods']['no_msaa']['gate']['objects'].items() if not v['passed']}
    return dict(candidates=len(rows), measured=len(measured), rgb_failures=rgb_failures,
        geometric_views=sum(r['methods']['no_msaa']['geometry_accepted'] for r in measured),
        usable_views=sum(r['methods']['no_msaa']['accepted'] for r in measured),
        best_index=best['index'], bottlenecks=bottlenecks), measured


def inspect_fits(folder):
    truth, fitted, errors = (read(folder / n) for n in ('private_truth.json', 'fits.json', 'private_errors.json'))
    values = []
    for fitrow, errorrow in zip(fitted['singles'], errors['singles'], strict=True):
        for strategy in ('original', 'repaired'):
            fit, reported = fitrow[strategy]['fit'], errorrow[strategy]
            center = math.dist(fit['center'], truth['center'])
            one, two = fit['axis'], truth['axis']
            cosine = abs(sum(a*b for a, b in zip(one, two))) / (math.hypot(*one)*math.hypot(*two))
            axis = math.degrees(math.acos(min(1., cosine)))
            assert math.isclose(center, reported['center_error_m'], abs_tol=1e-12)
            assert math.isclose(axis, reported['axis_error_deg'], abs_tol=1e-8)
            assert reported['accurate'] == (center <= .01 and axis <= 12)
            assert reported['accepted'] == fitrow[strategy]['quality_passed']
        assert errorrow['selective'] == errorrow[fitrow['choice']]
        values.append(errorrow['selective'])
    return values


def inspect_rays(rows, recorded):
    valid = [r for r in rows if r['ray_depth_m'] is not None]
    assert len(rows) == recorded['references'] and len(valid) == recorded['valid']
    for method in METHODS:
        errors = [abs(r[method]['depth_m'] - r['ray_depth_m']) for r in valid]
        result = recorded[method]
        assert math.isclose(sum(errors)/len(errors), result['mae_m'], abs_tol=1e-15)
        assert max(errors) == result['maximum_m']
        assert sum(e > .001 for e in errors) == result['errors_over_1mm']
        assert sum(r[method]['root'] != r['ray_root'] for r in valid) == result['root_mismatches']


def transitions(rows, field):
    def passed(row, method):
        value = row['methods'][method]
        return value['accepted'] if field == 'qualification' else value['calibration']['passed']
    pairs = [(passed(r, 'original'), passed(r, 'no_msaa')) for r in rows]
    return dict(total=len(pairs), original_pass=sum(a for a, b in pairs), no_msaa_pass=sum(b for a, b in pairs),
                gained=sum(not a and b for a, b in pairs), lost=sum(a and not b for a, b in pairs))


def verify_files():
    delivery = read(ROOT / 'evidence/DELIVERY.json')
    for name, expected in delivery['files'].items():
        assert digest(ROOT / 'evidence' / name) == expected, name
    manifest = read(RUN / 'manifest.json')
    checked = []
    for path, expected in manifest['identities'].items():
        if '/sensor_independent_v2/' in path:
            name = Path(path).name
            assert digest(REMOTE / name) == expected
            assert digest(ROOT / name) == expected
            checked.append(name)
    expected = read(RUN / '978401/result.json')['evidence']['no_msaa/qualified.png']
    assert digest(ROOT / 'evidence/images/978401_no_msaa_qualified.png') == expected
    return dict(text_files=len(delivery['files']), local_frozen_sources=len(checked), screenshot_verified=True)


def main():
    files = verify_files()
    audit = read(RUN / 'audit.json')
    layouts, all_rows, all_rays = {}, [], []
    fits = {m: [] for m in METHODS}
    for seed, recorded in audit['layouts'].items():
        folder = RUN / seed
        layouts[seed], rows = inspect_rows(folder, recorded)
        all_rows.extend(rows)
        rays = [r for p in sorted(folder.glob('pair_*/reference.json')) for r in read(p)['rays']]
        inspect_rays(rays, recorded['ray_statistics'])
        all_rays.extend(rays)
        for method in recorded['accepted']:
            fits[method].extend(inspect_fits(folder / method))
    inspect_rays(all_rays, audit['ray_statistics'])
    stats = {m: dict(observations=len(v), accurate=sum(r['accurate'] for r in v),
        accepted=sum(r['accepted'] for r in v), max_center_mm=max(r['center_error_m'] for r in v)*1000,
        max_axis_deg=max(r['axis_error_deg'] for r in v)) for m, v in fits.items()}
    for method, values in stats.items():
        saved = audit['metrics'][method]['singles']['qualified']['selective']
        assert all(values[k] == saved[k] for k in ('observations', 'accurate', 'accepted'))
    result = dict(passed=True, files=files, layouts=layouts, poses=stats,
        transitions={f: transitions(all_rows, f) for f in ('qualification', 'calibration')},
        rgb_failures=sum(v['rgb_failures'] for v in layouts.values()), rays_checked=len(all_rays),
        independent_numeric_recalculation=True, simulation_runs=0, refits=0,
        limitation='Large arrays independently audited remotely; local verification uses frozen text and screenshot')
    with (ROOT / 'evidence/local_verification.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
