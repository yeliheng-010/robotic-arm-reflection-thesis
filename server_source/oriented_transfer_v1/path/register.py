from pathlib import Path
from cc_common import save,sha,verify

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results'


def main():
    source=ROOT.parent/'tilt/results/manifest.json'
    previous=verify(source)
    assert verify(ROOT.parent/'tilt/results/result.json')['passed']
    assert not RUN.exists()
    identities=dict(previous['identities'])
    rows=[]
    for entry in previous['rows']:
        folder=ROOT.parent/'tilt/results/audit'/entry['name']
        result=verify(folder/'result.json')
        if result['endpoint_qualified']:
            identities.update(result['identities'])
            rows.append(dict(entry,endpoint_path=str(folder/'endpoints.jsonl')))
    assert rows
    paths=[source,*ROOT.glob('*.py'),*ROOT.glob('*.sbatch')]
    identities.update({str(p):sha(p) for p in paths})
    save(RUN/'manifest.json',dict(rows=rows,reused=previous['reused'],identities=identities,
        max_prefix=256,max_carry=512,max_process_seconds=600,physical_attempts=0,model_calls=0))


if __name__=='__main__':
    main()
