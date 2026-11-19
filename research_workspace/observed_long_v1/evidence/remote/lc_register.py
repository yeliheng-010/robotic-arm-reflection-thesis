from pathlib import Path
from cc_common import save,sha,verify

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'probe'


def main():
    assert not RUN.exists()
    source=ROOT.parent/'observed_yaw_v1/probe/manifest.json'
    previous=verify(source)
    assert verify(ROOT.parent/'observed_yaw_v1/probe/result.json')['passed']
    paths=[source,*ROOT.glob('*.py'),*ROOT.glob('*.sh'),*ROOT.glob('*.sbatch')]
    identities=dict(previous['identities'])
    identities.update({str(p):sha(p) for p in paths})
    save(RUN/'manifest.json',dict(rows=previous['rows'],identities=identities,max_pose_candidates=180,
        max_shift_m=.035,max_length_fraction=.30,min_aspect=3.,max_process_seconds=300,
        physical_attempts=0,model_calls=0))


if __name__ == '__main__':
    main()
