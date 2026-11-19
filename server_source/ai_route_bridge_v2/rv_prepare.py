import os
import subprocess
import sys
import unittest
from unittest.mock import patch
from rv_common import ROOT, SEEDS, read, save, sha, verify_parent
from pilot import extract_seeds
import nc_prepare


def main():
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'manifest.json').exists()
    inherited = verify_parent()
    assert read(ROOT.parent/'ai_route_bridge_v1/complete.json')['passed']
    suite = unittest.defaultTestLoader.discover(str(ROOT))
    tests = unittest.TextTestRunner(verbosity=2).run(suite)
    assert tests.wasSuccessful()
    subprocess.run([sys.executable, '-B', str(ROOT/'rv_audit.py'), '--help'], check=True)
    paths = set(ROOT.parent.glob('*/manifest.json')) | set(ROOT.parent.glob('*/protocol.json'))
    used = set()
    for path in paths:
        used.update(extract_seeds(read(path)))
    assert not used.intersection(SEEDS)
    with patch.object(nc_prepare, 'SEEDS', SEEDS):
        cases = nc_prepare.cases()
    for case in cases:
        case['item']['split'] = 'engineering_vertical_pilot_not_training'
        case['item']['id'] = 'V'+case['item']['id'][1:]
    identities = dict(inherited['identities'])
    parent = ROOT.parent/'ai_route_bridge_v1/manifest.json'
    identities[str(parent)] = sha(parent)
    identities.update({str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.md', '.sh', '.sbatch')})
    save(ROOT/'manifest.json', dict(cases=cases, identities=identities, seeds=list(SEEDS), tests=tests.testsRun,
        seed_isolation=dict(scanned=len(paths), overlap=False), max_attempts=24, max_model_calls=0, training_ready=False))
    print(dict(tests=tests.testsRun, conditions=len(cases), frozen=sha(ROOT/'manifest.json')), flush=True)


if __name__ == '__main__':
    main()
