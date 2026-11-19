from pathlib import Path
from cc_common import save,sha,verify

ROOT = Path(__file__).resolve().parent
RUN = ROOT/'probe'


def main():
    assert not RUN.exists()
    source = ROOT.parent/'joint_policy_v2/regression/manifest.json'
    previous = verify(source)
    rows = [r for r in previous['rows'] if not r['successful']]
    assert len(rows)==2
    paths = [source,*ROOT.glob('*.py'),*ROOT.glob('*.sh'),*ROOT.glob('*.sbatch')]
    identities = dict(previous['identities'])
    identities.update({str(p):sha(p) for p in paths})
    save(RUN/'manifest.json',dict(rows=rows,identities=identities,max_pose_candidates=90,
        yaw_degrees=[-15.,15.],max_process_seconds=300,physical_attempts=0,model_calls=0))


if __name__ == '__main__':
    main()
