from pathlib import Path
from cc_common import save,sha,verify

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'endpoints'


def main():
    assert not RUN.exists()
    source=ROOT.parent/'observed_long_v1/probe/manifest.json'
    previous=verify(source)
    assert verify(ROOT.parent/'observed_long_v1/probe/result.json')['passed']
    identities=dict(previous['identities'])
    rows=[]
    for entry in previous['rows']:
        folder=ROOT.parent/'observed_long_v1/probe/audit'/entry['name']
        result=verify(folder/'result.json')
        assert result['passed'] and not result['qualified'] and result['independent']
        identities.update(result['identities'])
        rows.append(dict(entry,long_plan=str(folder/'plan.json')))
    paths=[source,*ROOT.glob('*.py'),*ROOT.glob('*.sh'),*ROOT.glob('*.sbatch')]
    identities.update({str(p):sha(p) for p in paths})
    save(RUN/'manifest.json',dict(rows=rows,identities=identities,max_endpoint_checks=4096,
        max_process_seconds=600,physical_attempts=0,model_calls=0,
        purpose='private_oriented_endpoint_validation_not_AI_labels'))


if __name__=='__main__':
    main()
