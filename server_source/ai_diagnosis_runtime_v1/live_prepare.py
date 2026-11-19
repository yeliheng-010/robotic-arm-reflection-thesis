"""先测试和登记，再允许两次独立工程执行；不替换失败种子。"""
import os
from pathlib import Path
import unittest
from reflection.__main__ import bootstrap
bootstrap()
from sd_common import read, save, sha
from sd_config import factors
from sd_layout import sample
from sd_preflight import compiled_check
from loopstudy.actions import initial
from live_budget import apply_action

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
SEED = 962201
SCENES = ('baseline', 'varied_noisy')


def old_identities():
    previous = read(PARENT/'scene_pair_route_v3'/'manifest.json')
    for path, digest in previous['identities'].items():
        assert sha(path) == digest, path
    return previous['identities']


def seed_check():
    from pilot import extract_seeds
    paths = sorted(set(PARENT.glob('*/manifest.json')) | set(PARENT.glob('*/protocol.json')))
    used = set()
    for path in paths:
        used.update(extract_seeds(read(path)))
    assert SEED not in used, 'Registered seed already used; do not silently replace'
    return dict(scanned=len(paths), seed=SEED, overlap=False)


def cases():
    geometry = read(PARENT/'scene_diversity_v2'/'manifest.json')['geometry']
    layout = sample(SEED, geometry)
    state = apply_action(initial(), dict(id='SET_TIME_SCALE', args={'value': 1.5}))
    state = apply_action(state, dict(id='SET_GRASP_OFFSET', args={'delta_m': [.005, 0., 0.]}))
    rows = []
    for scene in SCENES:
        active = scene == 'varied_noisy'
        config = factors(SEED, 'combined' if active else 'baseline')
        config.update(group=scene, bodies=layout['bodies'] if active else {},
                      geometry_accepted=layout['accepted'] if active else True,
                      sensor=dict(depth_sigma_m=.003 if active else 0., dropout=.02 if active else 0.))
        config['compiled_check'] = compiled_check(config, geometry)
        item = dict(id=f'{SEED}_{scene}_wiring', seed=SEED, group=scene,
                    source='RedBlock', destination='BlueBin', fault='none', split='engineering_development')
        rows.append(dict(item=item, config=config, state=state))
    return rows


def main():
    assert os.environ.get('SLURM_JOB_ID')
    assert not (ROOT/'manifest.json').exists()
    suite = unittest.TestSuite([
        unittest.TestLoader().discover(str(ROOT)),
        unittest.TestLoader().discover(str(PARENT/'ai_diagnosis_v1')),
    ])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful()
    identities = dict(old_identities())
    source = PARENT/'ai_diagnosis_v1'
    for folder in (ROOT, source):
        for path in folder.iterdir():
            if path.suffix in ('.py', '.sh', '.sbatch', '.md'):
                identities[str(path)] = sha(path)
    isolation = seed_check()
    rows = cases()
    save(ROOT/'manifest.json', dict(seeds=[SEED], cases=rows, identities=identities,
         seed_isolation=isolation, tests=result.testsRun, max_new_attempts=2, max_attempts_per_case=1,
         model_smoke_max_calls=2, training_approved=False, test_used=False, promotion_allowed=False))
    print('Frozen two wiring conditions', sha(ROOT/'manifest.json'), 'tests', result.testsRun, flush=True)


if __name__ == '__main__':
    main()
