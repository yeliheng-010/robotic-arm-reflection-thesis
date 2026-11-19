"""复用明确的开发配置，不换种子；先冻结单次工程干预和源身份。"""
import os
from copy import deepcopy
import unittest
from reflection.__main__ import bootstrap
bootstrap()
from sd_preflight import compiled_check
from f_common import ROOT, PARENT, read, save, sha


def parent_identities():
    folder = PARENT/'ai_diagnosis_runtime_v1'
    identities = {}
    for name in ('manifest.json', 'revision_manifest.json', 'verification.json', 'coverage_verification.json'):
        value = read(folder/name)
        for path, digest in value['identities'].items():
            assert sha(path) == digest, path
            identities[path] = digest
        identities[str(folder/name)] = sha(folder/name)
    assert not read(folder/'coverage_verification.json')['authoritative_model_smoke_gate']
    return identities


def case():
    previous = read(PARENT/'ai_diagnosis_runtime_v1/manifest.json')
    row = deepcopy(next(r for r in previous['cases'] if r['item']['group'] == 'varied_noisy'))
    row['item'].update(id='962201_varied_noisy_engineering_stop', split='engineering_fixture_existing_development')
    geometry = read(PARENT/'scene_diversity_v2/manifest.json')['geometry']
    assert compiled_check(row['config'], geometry)['passed']
    return row


def main():
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'manifest.json').exists()
    folders = (ROOT, PARENT/'ai_diagnosis_runtime_v1', PARENT/'ai_diagnosis_v1')
    suite = unittest.TestSuite([unittest.TestLoader().discover(str(p)) for p in folders])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful()
    identities = parent_identities()
    for path in ROOT.iterdir():
        if path.suffix in ('.py', '.sh', '.sbatch', '.md'):
            identities[str(path)] = sha(path)
    value = dict(case=case(), identities=identities, tests=result.testsRun, seed_reused_intentionally=True,
                 max_new_attempts=1, max_model_calls=2, training_approved=False,
                 fixture='interrupt_after_move_to_point_before_release_then_cleanup_probe',
                 not_a_natural_failure_sample=True, model_snapshot_observation_index=0)
    save(ROOT/'manifest.json', value)
    print(dict(frozen=sha(ROOT/'manifest.json'), tests=result.testsRun, max_new_attempts=1), flush=True)


if __name__ == '__main__':
    main()
