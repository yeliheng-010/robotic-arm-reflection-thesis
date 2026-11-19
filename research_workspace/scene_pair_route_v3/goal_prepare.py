import unittest
from sd_common import read,save,sha
from goal_inputs import ROOT,PREVIOUS,inputs


def verify():
    manifest=read(ROOT/'manifest.json')
    for path,digest in manifest['identities'].items():
        assert sha(path)==digest,path
    return manifest


def main():
    assert not (ROOT/'manifest.json').exists()
    tests=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tests.wasSuccessful()
    preflight=read(ROOT/'preflight.json')
    assert preflight['passed']
    cases=inputs()
    from goal_audit_geometry import audit
    for case in cases:
        if not case['reused_success']:
            audit(case,read(ROOT/('preflight_'+case['id']+'.json')))
    identities=dict(read(PREVIOUS/'manifest.json')['identities'])
    files=[*ROOT.rglob('*.py'),*ROOT.glob('*.sh'),*ROOT.glob('*.sbatch'),ROOT/'PLAN.md',
           *ROOT.glob('preflight*.json'),*ROOT.glob('endpoints*.json'),PREVIOUS/'manifest.json',PREVIOUS/'verification.json']
    identities.update({str(p):sha(p) for p in files})
    for path,digest in identities.items():
        assert sha(path)==digest,path
    selected=[r['id'] for r in preflight['rows'] if r['selected'] is not None]
    save(ROOT/'manifest.json',dict(cases=cases,selected=selected,identities=identities,tests=tests.testsRun,
         max_attempts=3,max_new_per_task=1,model_calls=0,training_approved=False,promotion_allowed=False))
    print('Frozen',sha(ROOT/'manifest.json'),'selected',selected,flush=True)


if __name__=='__main__':
    main()
