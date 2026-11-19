"""描述正式数据筛选后的覆盖；不生成因果标签或修改训练门槛。"""
from bisect import bisect_right
from collections import Counter

SPLITS = ('train', 'dev')
CAMERA_EDGES = dict(azimuth_offset_deg=(-30., 0., 30.),
    elevation_deg=(45., 60.), distance_m=(1.1, 1.3), fovy=(50., 60.))
EXPECTED_NOISE = dict(depth_sigma_m=.003, dropout=.02)


def numeric(values, *, edges=()):
    counts = [0] * (len(edges) + 1)
    for value in values:
        counts[bisect_right(edges, value)] += 1
    return dict(min=min(values) if values else None, max=max(values) if values else None,
        edges=list(edges), histogram=counts, convention='left_closed_right_open')


def coverage(cases):
    values = [c for c in cases if c['item']['group'] == 'varied_noisy']
    assert len({c['item']['id'] for c in values}) == len(values)
    configs = {}
    for case in values:
        seed, config = case['item']['seed'], case['config']
        assert configs.setdefault(seed, config) == config, 'Environment mismatch within seed'
        assert config['sensor'] == EXPECTED_NOISE
    environments = list(configs.values())
    camera = {k: numeric([c['camera'][k] for c in environments], edges=edges)
        for k, edges in CAMERA_EDGES.items()}
    bodies = sorted({name for c in environments for name in c['bodies']})
    positions = {name: {axis: numeric([c['bodies'][name]['position'][i]
        for c in environments if name in c['bodies']])
        for i, axis in enumerate(('x', 'y', 'z'))} for name in bodies}
    objects = sorted({name for c in environments for name in c['appearance']})
    colors = {name: dict(Counter(c['appearance'][name]['color']
        for c in environments if name in c['appearance'])) for name in objects}
    return dict(conditions=len(values), seed_groups=len(configs), camera=camera,
        positions=positions, colors=colors, noise=EXPECTED_NOISE,
        tasks=dict(Counter(c['item']['source'] for c in values)))


def validate_rows(cases, rows):
    by_id = {c['item']['id']: c['item'] for c in cases}
    assert len(by_id) == len(cases), 'Duplicate condition'
    split_by_seed, snapshots = {}, {}
    for item in by_id.values():
        assert item['split'] in SPLITS
        assert split_by_seed.setdefault(item['seed'], item['split']) == item['split']
    for row in rows:
        item = by_id[row['condition']]
        assert all(row[k] == item[k] for k in ('seed', 'source', 'split'))
        identity = (row['seed'], row['source'], row['split'], row['condition'])
        assert snapshots.setdefault(row['snapshot_id'], identity) == identity
        assert not row['verified_recovery'] or row['eligible_natural']


def task_counts(rows):
    result = {}
    for split in SPLITS:
        natural = [r for r in rows if r['split'] == split and r['eligible_natural']]
        values = {}
        for task in sorted({r['source'] for r in natural}):
            selected = [r for r in natural if r['source'] == task]
            recovered = [r for r in selected if r['verified_recovery']]
            values[task] = dict(snapshots=len({r['snapshot_id'] for r in selected}),
                seeds=len({r['seed'] for r in selected}),
                recoveries=len({r['snapshot_id'] for r in recovered}),
                recovery_seeds=len({r['seed'] for r in recovered}))
        result[split] = values
    return result


def stages(cases, qualified_ids, rows):
    validate_rows(cases, rows)
    natural_ids = {r['condition'] for r in rows if r['eligible_natural']}
    recovered_ids = {r['condition'] for r in rows if r['verified_recovery']}
    assert recovered_ids <= natural_ids <= qualified_ids <= {c['item']['id'] for c in cases}
    selected = dict(proposed=cases,
        qualified=[c for c in cases if c['item']['id'] in qualified_ids],
        natural=[c for c in cases if c['item']['id'] in natural_ids],
        recovered=[c for c in cases if c['item']['id'] in recovered_ids])
    return {split: {name: coverage([c for c in group if c['item']['split'] == split])
        for name, group in selected.items()} for split in SPLITS}
