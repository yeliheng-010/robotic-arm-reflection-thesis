from pathlib import Path
from op_common import ROOT,TRIAL,verify,read,save,sha


def main():
    prior=verify(TRIAL/'manifest.json')
    assert read(TRIAL/'preflight_result.json')['passed']
    assert not (TRIAL/'cases').exists()
    paths=[TRIAL/'manifest.json',TRIAL/'preflight_result.json',*ROOT.glob('*.py'),*ROOT.glob('*.sbatch')]
    identities=dict(prior['identities'])
    identities.update({str(p):sha(p) for p in paths})
    save(TRIAL/'execution_manifest.json',dict(identities=identities,max_physical_attempts=1,
        model_calls=0,training_updates=0))


if __name__=='__main__':
    main()
