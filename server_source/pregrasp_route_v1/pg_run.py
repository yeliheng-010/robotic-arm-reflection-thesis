"""登记并核验独立版本，不修改已消费实验。"""
import sys
import subprocess
from pathlib import Path
from cc_common import read, save, sha, verify

ROOT = Path(__file__).resolve().parent
RUN = ROOT/'probe'
TIMEOUT_SECONDS = 900


def main():
    assert not RUN.exists()
    source = ROOT.parent/'clearance_pose_v1/probe'
    previous = verify(source/'manifest.json')
    result = verify(source/'result.json')
    assert result['passed'] and result['qualified'] == 0
    eligible = [r['id'] for r in result['rows'] if r['endpoints']['goals']['outcomes'].get('passed',0)>0]
    assert eligible == ['F0_964345_varied_noisy']
    identities = dict(previous['identities'], **result['identities'])
    paths = [source/'result.json', *ROOT.glob('*.py'), *ROOT.glob('*.sh'), *ROOT.glob('*.sbatch')]
    identities.update({str(p):sha(p) for p in paths})
    save(RUN/'manifest.json', dict(identities=identities, names=eligible,
        max_joint_candidates_per_prefix=63, physical_attempts=0, model_calls=0))
    for mode in ('probe','audit'):
        with (RUN/(mode+'.log')).open('x') as stream:
            subprocess.run([sys.executable,'-B',str(ROOT/'pg_probe.py'),mode],
                stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=TIMEOUT_SECONDS)
    result = verify(RUN/'audit/result.json')
    assert result['independent']
    verify(RUN/'manifest.json')
    save(RUN/'result.json', dict(passed=True, qualified=result['qualified'],
        physical_attempts=0, model_calls=0, identities={str(RUN/'audit/result.json'):sha(RUN/'audit/result.json')}))
    print(dict(passed=True, qualified=result['qualified']), flush=True)


if __name__ == '__main__':
    main()
