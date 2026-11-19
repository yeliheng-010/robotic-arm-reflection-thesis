import os
import sys
import subprocess
import unittest
from reflection.__main__ import bootstrap
bootstrap()
from pilot import extract_seeds
from sr_common import change as setup
from qp_common import verify as previous
from tp_common import ROOT, SOURCE, read, save, sha


def tests():
    loader = unittest.TestLoader()
    suite = loader.discover(str(ROOT))
    top_suite = unittest.TestLoader().discover(str(ROOT.parent/'observed_top_pose_v1'))
    suite.addTests(top_suite)
    tested = unittest.TextTestRunner(verbosity=2).run(suite)
    assert tested.wasSuccessful()
    for script in ('worker.py','audit.py'):
        subprocess.run([sys.executable, '-B', str(ROOT/script), '--help'], check=True)
    return tested.testsRun


def main():
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'manifest.json').exists()
    parent = previous()
    top = read(ROOT.parent/'observed_top_pose_v1/static/result.json')
    assert all(r['selected'] for r in top['rows'])
    assert all(sha(p) == h for p,h in top['identities'].items())
    tested = tests()
    reserved, result = read(SOURCE/'manifest.json'), read(SOURCE/'result.json')
    assert all(sha(p) == h for p,h in reserved['identities'].items())
    used = set()
    files = set(ROOT.parent.glob('*/manifest.json')) | set(ROOT.parent.glob('*/protocol.json'))
    for file in files-{SOURCE/'manifest.json'}:
        used.update(extract_seeds(read(file)))
    assert not used.intersection(reserved['seeds'])
    decisions, cases = {r['id']:r for r in result['rows']}, []
    for case in reserved['cases']:
        row = decisions[case['item']['id']]
        if not row['passed']:
            continue
        assert row['lift_height'] == .20 and sha(row['path']) == row['sha256']
        case['qualification'] = row
        case['item'].update(id='T'+case['item']['id'][1:], split='observed_top_capability_pilot_not_training')
        case['state'], _ = setup(case['state'], dict(grasp_mode='original'), action='SELF_SAFE_ROUTE')
        case['state']['parameters']['lift_height'] = .20
        cases.append(case)
    assert cases
    identities = dict(parent['identities'])
    identities.update(reserved['identities'])
    identities.update(top['identities'])
    paths = [SOURCE/'manifest.json', SOURCE/'result.json', ROOT.parent/'observed_top_pose_v1/static/result.json']
    paths += [p for folder in (ROOT, ROOT.parent/'observed_top_pose_v1') for p in folder.iterdir()
        if p.suffix in ('.py','.sh','.sbatch','.md')]
    identities.update({str(p):sha(p) for p in paths})
    save(ROOT/'manifest.json', dict(cases=cases, seeds=reserved['seeds'], identities=identities,
        tests=tested, max_attempts=3*len(cases), max_model_calls=0, training_ready=False,
        qualification_rows=result['rows'], seed_isolation=dict(reservation_only_reuse=True, overlap=False)))
    print(dict(conditions=len(cases), max_attempts=3*len(cases)), flush=True)


if __name__ == '__main__':
    main()
