import os
import unittest
import subprocess
import sys
from unittest.mock import patch
from sr_common import ROOT, SEEDS, read, save, sha, verify_parent
from pilot import extract_seeds
import nc_prepare


def main():
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'manifest.json').exists()
    parent = verify_parent()
    suite = unittest.defaultTestLoader.discover(str(ROOT))
    tested = unittest.TextTestRunner(verbosity=2).run(suite)
    assert tested.wasSuccessful()
    subprocess.run([sys.executable, '-B', str(ROOT/'sr_audit.py'), '--help'], check=True)
    paths = set(ROOT.parent.glob('*/manifest.json')) | set(ROOT.parent.glob('*/protocol.json'))
    used = set()
    for path in paths:
        used.update(extract_seeds(read(path)))
    assert not used.intersection(SEEDS)
    with patch.object(nc_prepare, 'SEEDS', SEEDS):
        cases = nc_prepare.cases()
    for case in cases:
        case['item']['id'] = 'S'+case['item']['id'][1:]
        case['item']['split'] = 'engineering_self_collision_pilot_not_training'
    identities = dict(parent['identities'])
    for folder in (ROOT, ROOT.parent/'natural_self_guard_v1', ROOT.parent/'scene_pair_contact_diagnostic_v1'):
        identities.update({str(p):sha(p) for p in folder.iterdir() if p.suffix in ('.py', '.sh', '.md', '.sbatch')})
    save(ROOT/'manifest.json', dict(cases=cases, identities=identities, seeds=list(SEEDS), tests=tested.testsRun,
        seed_isolation=dict(scanned=len(paths), overlap=False), max_attempts=24, max_model_calls=0,
        training_ready=False, self_collision_guard='all_attempts', contact_capture='private_engineering_only'))
    print(dict(conditions=len(cases), tests=tested.testsRun, frozen=sha(ROOT/'manifest.json')), flush=True)


if __name__ == '__main__':
    main()
