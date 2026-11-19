from pathlib import Path
from cc_common import read,save,sha,verify

ROOT = Path(__file__).resolve().parent
RUN = ROOT/'regression'


def main():
    assert not RUN.exists()
    source = ROOT.parent/'joint_policy_v1/regression/manifest.json'
    previous = verify(source)
    identities = dict(previous['identities'])
    paths = [source,*ROOT.glob('*.py'),*ROOT.glob('*.sh'),*ROOT.glob('*.sbatch')]
    identities.update({str(p):sha(p) for p in paths})
    save(RUN/'manifest.json',dict(rows=previous['rows'],identities=identities,
        change='Independent candidate-stage ledgers; same observation and safety checks',
        physical_attempts=0,model_calls=0))


if __name__ == '__main__':
    main()
