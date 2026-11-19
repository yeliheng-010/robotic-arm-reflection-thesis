from pathlib import Path
from cc_common import save,sha,verify

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results'


def main():
    source=ROOT.parent/'endpoints_v2/manifest.json'
    previous=verify(source)
    result=ROOT.parent/'endpoints_v2/result.json'
    assert verify(result)['passed']
    assert not RUN.exists()
    identities=dict(previous['identities'])
    paths=[source,result,*ROOT.glob('*.py'),*ROOT.glob('*.sbatch')]
    identities.update({str(p):sha(p) for p in paths})
    save(RUN/'manifest.json',dict(rows=previous['rows'],reused=previous['reused'],identities=identities,
        max_endpoint_checks=2048,max_process_seconds=600,max_grasp_poses=2,
        pitches_degrees=[0.,15.,-15.,30.,-30.],release_configs=8,physical_attempts=0,model_calls=0))


if __name__=='__main__':
    main()
