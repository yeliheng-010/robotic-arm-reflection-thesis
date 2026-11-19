"""旧案例真实记录门禁、新种子检查及场景冻结。"""
import unittest
from sd_common import read, save, sha, verify
from sd_config import factors
from sd_layout import sample
from sd_preflight import compiled_check
from pair_config import NOISE_SIGMA_M, NOISE_DROPOUT
from pv_protocol import ROOT, SEEDS, SCENES, items


def anchor_gate():
    parent = ROOT.parent
    for scene in SCENES:
        old = read(parent/'scene_pair_v1'/'smoke'/scene/'result.json')
        new = read(parent/'scene_pair_v2'/'anchor'/scene/'result.json')
        assert new['success']
        count = 1 if scene == 'baseline' else 2
        for index in range(count):
            a = read(old['steps'][index]['result_path'])['records'][0]
            b = read(new['steps'][index]['result_path'])['records'][0]
            for key in ('candidate_trace', 'domain_randomization', 'parameters', 'execution_adapter', 'evaluation'):
                assert a[key] == b[key]
    record = read(new['steps'][-1]['result_path'])['records'][0]
    motion = record['motion_extension']
    assert record['physical_success'] and motion['active']
    assert motion['candidates'][motion['selected']]['id'].startswith('world_down')
    return dict(passed=True, baseline_preserved=True, enhanced_gain=True, identical_prefix=True)


def unused():
    from pilot import extract_seeds
    paths = set(ROOT.parent.glob('*/manifest.json')) | set(ROOT.parent.glob('*/protocol.json'))
    used = set()
    for path in paths:
        used.update(extract_seeds(read(path)))
    assert not used.intersection(SEEDS), 'New seed already used'
    return dict(scanned=len(paths), overlap=[])


def configurations(geometry):
    configs, layouts = {}, {}
    for seed in SEEDS:
        layout = sample(seed, geometry)
        layouts[str(seed)] = layout
        for scene in SCENES:
            active = scene == 'varied_noisy'
            config = factors(seed, 'combined' if active else 'baseline')
            config.update(group=scene, bodies=layout['bodies'] if active else {},
                          geometry_accepted=layout['accepted'] if active else True,
                          sensor=dict(depth_sigma_m=NOISE_SIGMA_M if active else 0.,
                                      dropout=NOISE_DROPOUT if active else 0.))
            config['compiled_check'] = compiled_check(config, geometry)
            configs[f'{seed}_{scene}'] = config
    return configs, layouts


def identities(previous):
    paths = set(previous['identities'])
    for folder in (ROOT, ROOT.parent/'scene_pair_v2', ROOT.parent/'scene_pair_v1'):
        paths.update(str(p) for p in folder.iterdir() if p.suffix in ('.py', '.sh', '.sbatch'))
    paths.add(str(ROOT.parent/'scene_diversity_v2'/'manifest.json'))
    return {path: sha(path) for path in sorted(paths)}


def main():
    assert not (ROOT/'manifest.json').exists(), 'Preserve frozen manifest'
    suite = unittest.defaultTestLoader.discover(str(ROOT), pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful()
    previous = verify()
    gate, isolation = anchor_gate(), unused()
    configs, layouts = configurations(previous['geometry'])
    manifest = dict(seeds=list(SEEDS), items=items(), configs=configs, layouts=layouts,
                    identities=identities(previous), anchor_gate=gate, seed_isolation=isolation,
                    test_used=False, training_approved=False, model_calls=0,
                    comparison='shared_prefix_then_paired_third_attempt_when_eligible')
    save(ROOT/'manifest.json', manifest)
    save(ROOT/'preflight.json', dict(passed=True, tests=result.testsRun, conditions=len(items()),
         manifest_sha256=sha(ROOT/'manifest.json'), geometry_rejected=sum(
             not c['geometry_accepted'] or not c['compiled_check']['passed'] for c in configs.values())))
    print('FROZEN 48 conditions, 2 scenes', flush=True)


if __name__ == '__main__':
    main()
