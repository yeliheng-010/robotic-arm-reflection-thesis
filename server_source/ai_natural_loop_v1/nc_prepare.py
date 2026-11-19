import os
from copy import deepcopy
import unittest
from reflection.__main__ import bootstrap
bootstrap()
from pilot import extract_seeds
from sd_layout import sample
from sd_config import factors, PAIRS
from sd_preflight import compiled_check
from loopstudy.actions import initial
from nc_common import ROOT, PARENT, SEEDS, read, save, sha


def identities():
    source = PARENT/'ai_diagnosis_failure_v1'
    result = {}
    for name in ('manifest.json', 'audit_revision_manifest.json', 'verification.json',
                 'model_manifest.json', 'model_verification.json'):
        value = read(source/name)
        for path, digest in value['identities'].items():
            assert sha(path) == digest, path
            result[path] = digest
        result[str(source/name)] = sha(source/name)
    assert read(source/'verification.json')['model_smoke_gate']
    assert read(source/'model_verification.json')['valid_proposals'] == 2
    for path in ROOT.iterdir():
        if path.suffix in ('.py', '.sh', '.sbatch', '.md'):
            result[str(path)] = sha(path)
    return result


def unused():
    paths = sorted(set(PARENT.glob('*/manifest.json')) | set(PARENT.glob('*/protocol.json')))
    used = set()
    for path in paths:
        used.update(extract_seeds(read(path)))
    assert not used.intersection(SEEDS), 'Do not silently replace used seeds'
    return dict(scanned=len(paths), seeds=list(SEEDS), overlap=False)


def cases():
    geometry = read(PARENT/'scene_diversity_v2/manifest.json')['geometry']
    rows = []
    for seed in SEEDS:
        layout = sample(seed, geometry)
        for scene in ('baseline', 'varied_noisy'):
            active = scene == 'varied_noisy'
            config = factors(seed, 'combined' if active else 'baseline')
            config.update(group=scene, bodies=layout['bodies'] if active else {},
                geometry_accepted=layout['accepted'] if active else True,
                sensor=dict(depth_sigma_m=.003 if active else 0., dropout=.02 if active else 0.))
            config['compiled_check'] = compiled_check(config, geometry)
            for index, (source, destination) in enumerate(PAIRS):
                item = dict(id=f'N{index}_{seed}_{scene}', source=source, destination=destination,
                            seed=seed, group=scene, fault='none', split='pilot_development_not_training')
                rows.append(dict(item=item, config=deepcopy(config), state=initial()))
    return rows


def main():
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'manifest.json').exists()
    folders = (ROOT, PARENT/'ai_diagnosis_failure_v1', PARENT/'ai_diagnosis_runtime_v1', PARENT/'ai_diagnosis_v1')
    suite = unittest.TestSuite([unittest.TestLoader().discover(str(p)) for p in folders])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful()
    isolation = unused()
    rows = cases()
    save(ROOT/'manifest.json', dict(cases=rows, identities=identities(), tests=result.testsRun,
         seeds=list(SEEDS), seed_isolation=isolation, max_attempts_per_trajectory=3, max_extra_observations=2,
         max_new_attempts=56, max_model_calls=64, max_calls_per_model_trajectory=4,
         training_approved=False, first_stage_seed=SEEDS[0], inherited_engineering_completed=True))
    print(dict(frozen=sha(ROOT/'manifest.json'), tests=result.testsRun, conditions=len(rows)), flush=True)


if __name__ == '__main__':
    main()
