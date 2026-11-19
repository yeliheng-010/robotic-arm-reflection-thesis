import os
import unittest
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
from pilot import extract_seeds
import nc_prepare
import rb_audit
from rb_common import ROOT, SEEDS, save, read, sha, verify_parent


def main():
    assert os.environ.get('SLURM_JOB_ID')
    assert not (ROOT/'manifest.json').exists()
    inherited = verify_parent()
    assert read(ROOT.parent/'ai_natural_loop_v1/complete.json')['passed']
    tests = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tests.wasSuccessful()
    paths = set(ROOT.parent.glob('*/manifest.json')) | set(ROOT.parent.glob('*/protocol.json'))
    used = set()
    for path in paths:
        used.update(extract_seeds(read(path)))
    assert not used.intersection(SEEDS)
    with patch.object(nc_prepare, 'SEEDS', SEEDS):
        cases = nc_prepare.cases()
    for case in cases:
        case['item']['split'] = 'engineering_capability_pilot_not_training'
        case['item']['id'] = 'R'+case['item']['id'][1:]
    identities = dict(inherited['identities'])
    identities[str(ROOT.parent/'ai_natural_loop_v1/manifest.json')] = sha(ROOT.parent/'ai_natural_loop_v1/manifest.json')
    identities.update({str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.md', '.sh', '.sbatch')})
    save(ROOT/'manifest.json', dict(cases=cases, identities=identities, seeds=list(SEEDS), tests=tests.testsRun,
        seed_isolation=dict(scanned=len(paths), overlap=False), max_attempts=24, max_model_calls=0, training_ready=False))
    print(dict(tests=tests.testsRun, conditions=len(cases), frozen=sha(ROOT/'manifest.json')), flush=True)


if __name__ == '__main__':
    main()
