import os
import sys
import subprocess
import unittest
from sr_common import change as setup
from pilot import extract_seeds
from qp_common import verify as previous
from nd_common import ROOT, SOURCE, read, save, sha


def main():
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'manifest.json').exists()
    parent = previous()
    reserved, result = read(SOURCE/'manifest.json'), read(SOURCE/'result.json')
    assert all(sha(p) == h for p, h in reserved['identities'].items())
    tested = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tested.wasSuccessful()
    subprocess.run([sys.executable, '-B', str(ROOT/'audit.py'), '--help'], check=True)
    files = set(ROOT.parent.glob('*/manifest.json')) | set(ROOT.parent.glob('*/protocol.json'))
    used = set()
    for file in files-{SOURCE/'manifest.json'}:
        used.update(extract_seeds(read(file)))
    assert not used.intersection(reserved['seeds'])
    decisions = {r['id']: r for r in result['rows']}
    cases = []
    for case in reserved['cases']:
        row = decisions[case['item']['id']]
        if row['passed']:
            assert sha(row['path']) == row['sha256']
            case['qualification'] = row
            case['item']['id'] = 'D'+case['item']['id'][1:]
            case['item']['split'] = 'deeper_capability_pilot_not_training'
            case['state'], _ = setup(case['state'], dict(grasp_mode='original'), action='SELF_SAFE_ROUTE')
            cases.append(case)
    identities = dict(parent['identities'], **reserved['identities'])
    paths = [SOURCE/'manifest.json', SOURCE/'result.json']
    paths += [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sbatch', '.md')]
    identities.update({str(p): sha(p) for p in paths})
    save(ROOT/'manifest.json', dict(cases=cases, seeds=reserved['seeds'], identities=identities,
        tests=tested.testsRun, max_attempts=3*len(cases), max_model_calls=0, training_ready=False,
        qualification_rows=result['rows'], seed_isolation=dict(reservation_only_reuse=True, overlap=False)))
    print(dict(conditions=len(cases), max_attempts=3*len(cases)), flush=True)


if __name__ == '__main__':
    main()
