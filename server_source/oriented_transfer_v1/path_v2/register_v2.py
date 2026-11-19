from pathlib import Path
from cc_common import save,sha,verify

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results'


def main():
    source=ROOT.parent/'path/results/manifest.json'
    previous=verify(source)
    assert verify(ROOT.parent/'path/results/result.json')['passed']
    assert not RUN.exists()
    identities=dict(previous['identities'])
    paths=[source,*ROOT.glob('*.py'),*ROOT.glob('*.sbatch')]
    identities.update({str(p):sha(p) for p in paths})
    save(RUN/'manifest.json',dict(rows=previous['rows'],reused=previous['reused'],identities=identities,
        max_prefix=256,max_carry=512,max_process_seconds=600,physical_attempts=0,model_calls=0,
        revision='Monotonic escape of existing support geometry pairs; modular search'))


if __name__=='__main__':
    main()
