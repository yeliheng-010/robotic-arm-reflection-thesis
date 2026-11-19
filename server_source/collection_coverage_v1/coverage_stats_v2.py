"""分解覆盖聚合，保持v1数值行为；原冻结文件不修改。"""
from collections import Counter
from coverage_stats import CAMERA_EDGES, EXPECTED_NOISE, SPLITS, numeric, validate_rows


def environments(cases):
    assert len({c['item']['id'] for c in cases}) == len(cases)
    configs = {}
    for case in cases:
        seed, config = case['item']['seed'], case['config']
        assert configs.setdefault(seed, config) == config, 'Environment mismatch within seed'
        assert config['sensor'] == EXPECTED_NOISE
    return list(configs.values())


def camera_coverage(configs):
    return {key: numeric([c['camera'][key] for c in configs], edges=edges)
        for key, edges in CAMERA_EDGES.items()}


def body_positions(configs, name):
    positions = [c['bodies'][name]['position'] for c in configs if name in c['bodies']]
    return {axis: numeric([p[i] for p in positions]) for i, axis in enumerate(('x', 'y', 'z'))}


def position_coverage(configs):
    names = sorted({name for c in configs for name in c['bodies']})
    return {name: body_positions(configs, name) for name in names}


def object_colors(configs, name):
    return dict(Counter(c['appearance'][name]['color']
        for c in configs if name in c['appearance']))


def color_coverage(configs):
    names = sorted({name for c in configs for name in c['appearance']})
    return {name: object_colors(configs, name) for name in names}


def coverage(cases):
    values = [c for c in cases if c['item']['group'] == 'varied_noisy']
    configs = environments(values)
    return dict(conditions=len(values), seed_groups=len(configs), camera=camera_coverage(configs),
        positions=position_coverage(configs), colors=color_coverage(configs), noise=EXPECTED_NOISE,
        tasks=dict(Counter(c['item']['source'] for c in values)))


def counts(rows):
    recovered = [r for r in rows if r['verified_recovery']]
    return dict(snapshots=len({r['snapshot_id'] for r in rows}),
        seeds=len({r['seed'] for r in rows}),
        recoveries=len({r['snapshot_id'] for r in recovered}),
        recovery_seeds=len({r['seed'] for r in recovered}))


def split_task_counts(rows, split):
    natural = [r for r in rows if r['split'] == split and r['eligible_natural']]
    tasks = sorted({r['source'] for r in natural})
    return {task: counts([r for r in natural if r['source'] == task]) for task in tasks}


def task_counts(rows):
    return {split: split_task_counts(rows, split) for split in SPLITS}


def stage_ids(cases, qualified_ids, rows):
    validate_rows(cases, rows)
    proposed = {c['item']['id'] for c in cases}
    natural = {r['condition'] for r in rows if r['eligible_natural']}
    recovered = {r['condition'] for r in rows if r['verified_recovery']}
    assert recovered <= natural <= qualified_ids <= proposed
    return dict(proposed=proposed, qualified=qualified_ids, natural=natural, recovered=recovered)


def split_stages(cases, stages_by_id, split):
    values = [c for c in cases if c['item']['split'] == split]
    return {name: coverage([c for c in values if c['item']['id'] in ids])
        for name, ids in stages_by_id.items()}


def stages(cases, qualified_ids, rows):
    identifiers = stage_ids(cases, qualified_ids, rows)
    return {split: split_stages(cases, identifiers, split) for split in SPLITS}
