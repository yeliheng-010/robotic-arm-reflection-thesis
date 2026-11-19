"""本地独立数值复核；不启动仿真、重渲染或重拟合。"""
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from sensor_independent_v2.verify_delivery import inspect_rays

ROOT = Path(__file__).resolve().parent
REMOTE = ROOT / 'evidence/remote'
RUN = REMOTE / 'run'
METHODS = ('joint', 'adaptive')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_fits(folder):
    truth = read(folder / 'private_truth.json')
    fits, errors = read(folder / 'fits.json')['singles'], read(folder / 'private_errors.json')['singles']
    selected = []
    for fitrow, errorrow in zip(fits, errors, strict=True):
        for name in ('original', 'repaired'):
            fit, reported = fitrow[name]['fit'], errorrow[name]
            if fit is None:
                assert not reported['accurate'] and reported['center_error_m'] is None
                assert not reported['accepted']
                continue
            center = math.dist(fit['center'], truth['center'])
            cosine = abs(sum(a*b for a, b in zip(fit['axis'], truth['axis'])))
            angle = math.degrees(math.acos(min(1., cosine)))
            assert math.isclose(center, reported['center_error_m'], abs_tol=1e-12)
            assert math.isclose(angle, reported['axis_error_deg'], abs_tol=1e-8)
            assert reported['accurate'] == (center <= .01 and angle <= 12)
            assert reported['accepted'] == fitrow[name]['quality_passed']
        if fitrow['choice'] is None:
            assert not fitrow['original']['quality_passed'] and not fitrow['repaired']['quality_passed']
            assert errorrow['selective'] == dict(accurate=False, accepted=False, center_error_m=None, axis_error_deg=None)
        else:
            assert errorrow['selective'] == errorrow[fitrow['choice']]
        selected.append(errorrow['selective'])
    return selected


def compare(before, after):
    delta = np.abs(before.astype(np.int16)-after.astype(np.int16))
    pixels = np.any(delta != 0, axis=-1)
    maximum, fraction = int(delta.max()), float(pixels.mean())
    return dict(passed=maximum <= 2 and fraction <= .001, max_channel_delta=maximum,
        changed_fraction=fraction, changed_pixels=int(pixels.sum()), bitwise_equal=not bool(pixels.any()),
        before_sha256=hashlib.sha256(before.tobytes()).hexdigest(),
        after_sha256=hashlib.sha256(after.tobytes()).hexdigest(), shape=list(before.shape))


def check_arrays(uid, row):
    path = ROOT / f'evidence/arrays/978501_rgb_{uid}.npz'
    assert sha(path) == read(RUN / '978501/result.json')['evidence'][f'rgb_{uid}.npz']
    with np.load(path) as packed:
        first = packed['first'].astype(np.int32)
        images = [first]
        for difference in packed['deltas']:
            images.append(images[-1] + difference.astype(np.int32))
    assert all(np.all((v >= 0) & (v <= 255)) for v in images)
    images = [v.astype(np.uint8) for v in images]
    rgb = row['rgb']
    assert len(images) == rgb['stability']['count']+1
    assert [compare(a, b) for a, b in zip(images[:-2], images[1:-1])] == rgb['stability']['checks']
    assert compare(images[-2], images[-1]) == rgb['post']
    assert compare(images[0], images[-1]) == rgb['initial']


def rgb_check(rgb):
    checks = rgb['stability']['checks']
    streak = 0
    for i, check in enumerate(checks):
        assert streak < 2
        streak = streak+1 if check['passed'] else 0
    assert len(checks)+1 == rgb['stability']['count'] <= 4
    assert rgb['stability']['passed'] == (streak >= 2)
    for check in checks + [rgb['post'], rgb['initial']]:
        assert check['passed'] == (check['max_channel_delta'] <= 2 and check['changed_fraction'] <= .001)
        assert check['changed_fraction'] == check['changed_pixels'] / (check['shape'][0]*check['shape'][1])
    assert rgb['eligible'] == (rgb['stability']['passed'] and rgb['post']['passed'])


def layout(seed, recorded):
    folder = RUN / seed
    rows = read(folder / 'observations.json')
    assert rows == [json.loads(s) for s in (folder / 'observations.jsonl').read_text(encoding='utf-8').splitlines()]
    measured = [r for r in rows if 'rgb' in r]
    for row in measured:
        rgb_check(row['rgb'])
        assert row['geometry_accepted'] == (row['gate']['passed'] and row['calibration']['passed'])
        assert row['accepted'] == (row['geometry_accepted'] and row['rgb']['eligible'])
    searches, stats, errors = read(folder / 'searches.json'), {}, {}
    for method, entries in searches.items():
        selected = [rows[e['uid']] for e in entries]
        usable = [i for i, r in enumerate(selected) if r['accepted']]
        stats[method] = dict(candidates=len(selected), measured=sum('rgb' in r for r in selected),
            geometric=sum(r.get('geometry_accepted', False) for r in selected), usable=len(usable))
        assert stats[method] == recorded['search_statistics'][method]
        if usable:
            assert usable[0] == recorded['accepted'][method]['index']
            errors[method] = inspect_fits(folder / method)
        else:
            best = min((r for r in selected if 'gate' in r), key=lambda r: (len(r['gate']['rejected']), r['index']))
            stats[method]['diagnostic_best_uid'] = best['index']
            stats[method]['bottlenecks'] = {n: g['reasons'] for n, g in best['gate']['objects'].items() if not g['passed']}
    rays = [r for p in sorted(folder.glob('pair_*/reference.json')) for r in read(p)['rays']]
    inspect_rays(rays, recorded['ray_statistics'])
    return stats, errors, rays, measured


def verify_files():
    delivered = read(ROOT / 'evidence/DELIVERY.json')
    for name, expected in delivered['files'].items():
        assert sha(ROOT / 'evidence' / name) == expected
    manifest = read(RUN / 'manifest.json')
    sources = dict(manifest['identities'])
    sources.update(read(RUN / 'audit_started_978502.json')['sources'])
    count = 0
    for path, expected in sources.items():
        if '/observation_search_v1/' in path:
            assert sha(ROOT / Path(path).name) == expected
            assert sha(REMOTE / Path(path).name) == expected
            count += 1
    rows = read(RUN / '978501/observations.json')
    for uid in (76, 133):
        check_arrays(uid, rows[uid])
    return dict(text_files=len(delivered['files']), verified_source_files=count, raw_rgb_sequences=2)


def main():
    files = verify_files()
    audit = read(RUN / 'audit.json')
    layouts, rays, measured = {}, [], []
    errors = {m: [] for m in METHODS}
    for seed, recorded in audit['layouts'].items():
        stats, poses, references, views = layout(seed, recorded)
        layouts[seed] = stats
        rays.extend(references)
        measured.extend(views)
        for method, values in poses.items():
            errors[method].extend(values)
    inspect_rays(rays, audit['ray_statistics'])
    rgb = dict(measured=len(measured), first_to_final_failures=sum(not r['rgb']['initial']['passed'] for r in measured),
        first_adjacent_failures=sum(not r['rgb']['stability']['checks'][0]['passed'] for r in measured),
        stability_failures=sum(not r['rgb']['stability']['passed'] for r in measured),
        post_failures=sum(not r['rgb']['post']['passed'] for r in measured),
        recovered=sum(not r['rgb']['initial']['passed'] and r['rgb']['eligible'] for r in measured),
        frames=sum(r['rgb']['stability']['count'] for r in measured))
    assert rgb == audit['rgb_statistics']
    poses = {m: dict(count=len(v), accurate=sum(r['accurate'] for r in v),
        accepted=sum(r['accepted'] for r in v), max_accepted_center_mm=max((r['center_error_m'] for r in v if r['accepted']), default=0)*1000,
        max_accepted_axis_deg=max((r['axis_error_deg'] for r in v if r['accepted']), default=0)) for m, v in errors.items()}
    for method, stats in poses.items():
        stored = audit['metrics'][method]['singles']['qualified']['selective']
        assert stats['count'] == stored['observations']
        assert stats['accurate'] == stored['accurate'] and stats['accepted'] == stored['accepted']
    result = dict(passed=True, files=files, layouts=layouts, rgb=rgb, poses=poses, rays_checked=len(rays),
        simulation_runs=0, refits=0, verification_source_sha256=sha(Path(__file__)))
    with (ROOT / 'evidence/local_verification.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
