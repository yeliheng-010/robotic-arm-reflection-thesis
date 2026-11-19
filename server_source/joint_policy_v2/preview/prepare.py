from pathlib import Path
from cc_common import save,sha,verify

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'run'
REGRESSION=ROOT.parent/'regression'


def main():
    assert not RUN.exists()
    previous=verify(REGRESSION/'manifest.json')
    assert verify(REGRESSION/'result.json')['passed']
    rows=[r for r in previous['rows'] if r['name'] in ('old_964008','new_964345')]
    assert len(rows)==2
    identities=dict(previous['identities'])
    paths=[REGRESSION/'result.json',*ROOT.glob('*.py'),*ROOT.glob('*.sbatch')]
    for entry in rows:
        audit=REGRESSION/'audit'/entry['name']/'result.json'
        checked=verify(audit)
        assert checked['passed'] and checked['qualified'] and checked['independent']
        identities.update(checked['identities'])
        paths.append(audit)
    identities.update({str(p):sha(p) for p in paths})
    save(RUN/'manifest.json',dict(rows=rows,identities=identities,physical_attempts=0,model_calls=0))


if __name__ == '__main__':
    main()
