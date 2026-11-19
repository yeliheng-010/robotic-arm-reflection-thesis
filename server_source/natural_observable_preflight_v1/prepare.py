import os
import unittest
from pathlib import Path
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import nc_prepare
from pilot import extract_seeds
from sd_preflight import project_modules
from qp_common import verify as verify_parent
from common import ROOT, SEEDS, read, save, sha


def main():
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'manifest.json').exists()
    previous = verify_parent()
    tested = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tested.wasSuccessful()
    paths = set(ROOT.parent.glob('*/manifest.json')) | set(ROOT.parent.glob('*/protocol.json'))
    used = set()
    for path in paths:
        used.update(extract_seeds(read(path)))
    assert not used.intersection(SEEDS)
    with patch.object(nc_prepare, 'SEEDS', SEEDS):
        cases = nc_prepare.cases()
    cases = [c for c in cases if c['item']['group'] == 'varied_noisy' or c['item']['seed'] == SEEDS[0]]
    for case in cases:
        case['item']['id'] = 'O'+case['item']['id'][1:]
        case['item']['split'] = 'observable_qualification_pilot_not_training'
    identities = dict(previous['identities'])
    files = [*ROOT.glob('*.py'), *ROOT.glob('*.sbatch'), ROOT/'PLAN.md']
    files += [Path(p) for p in project_modules()]
    files += list((ROOT.parent/'natural_feasibility_v1').glob('*.py'))
    identities.update({str(p): sha(p) for p in files})
    save(ROOT/'manifest.json', dict(cases=cases, seeds=list(SEEDS), identities=identities,
        seed_isolation=dict(scanned=len(paths), overlap=False), tests=tested.testsRun,
        reserved_for_new_physics=True, training_ready=False, physical_attempts=0, model_calls=0))
    print(dict(conditions=len(cases), tests=tested.testsRun), flush=True)


if __name__ == '__main__':
    main()
