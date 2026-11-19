import os
import sys
import unittest
import subprocess
from qp_common import ROOT,SOURCE,read,save,sha,verify_parent
from sr_common import change
from pilot import extract_seeds


def main():
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'manifest.json').exists()
    parent=verify_parent()
    reservation,qualified=read(SOURCE/'manifest.json'),read(SOURCE/'result.json')
    assert all(sha(p)==h for p,h in reservation['identities'].items())
    assert all(sha(p)==h for p,h in qualified['identities'].items())
    tested=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tested.wasSuccessful()
    subprocess.run([sys.executable,'-B',str(ROOT/'qp_audit.py'),'--help'],check=True)
    paths=set(ROOT.parent.glob('*/manifest.json'))|set(ROOT.parent.glob('*/protocol.json'))
    used=set()
    for path in paths-{SOURCE/'manifest.json'}:
        used.update(extract_seeds(read(path)))
    assert not used.intersection(reservation['seeds'])
    decisions={r['id']:r for r in qualified['rows']}
    cases=[]
    for case in reservation['cases']:
        row=decisions[case['item']['id']]
        if not row['passed']:
            continue
        assert sha(row['path'])==row['sha256']
        case['qualification']=row
        case['item']['id']='C'+case['item']['id'][1:]
        case['item']['split']='qualified_executor_pilot_not_training'
        case['state'],_=change(case['state'],dict(grasp_mode='original'),action='SELF_SAFE_ROUTE')
        cases.append(case)
    identities=dict(parent['identities'])
    identities.update(reservation['identities'])
    identities.update(qualified['identities'])
    for path in [SOURCE/'manifest.json',SOURCE/'result.json',*ROOT.iterdir()]:
        if path.is_file() and path.suffix in ('.py','.sh','.sbatch','.md','.json'):
            identities[str(path)]=sha(path)
    save(ROOT/'manifest.json',dict(cases=cases,identities=identities,seeds=reservation['seeds'],
        qualification_rows=qualified['rows'],seed_isolation=dict(scanned=len(paths),
            reservation_only_reuse=True,overlap=False),tests=tested.testsRun,max_attempts=3*len(cases),
        max_model_calls=0,training_ready=False,initial_control=dict(grasp_mode='world_down')))
    print(dict(conditions=len(cases),max_attempts=3*len(cases),tests=tested.testsRun),flush=True)


if __name__=='__main__':
    main()
