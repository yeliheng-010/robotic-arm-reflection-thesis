import os
import subprocess
import sys
from pathlib import Path
from f_common import read, save, sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'safe_visual_preflight_v1'


def main():
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'manifest.json').exists()
    original, old = read(SOURCE/'manifest.json'), read(SOURCE/'result.json')
    guard = read(ROOT.parent/'natural_span_guard_v1/runtime_check/verification.json')
    for source in (original, guard):
        assert all(sha(p) == h for p,h in source['identities'].items())
    assert not (ROOT.parent/'ai_safe_visual_loop_v1/started.json').exists()
    admitted = {r['id'] for r in old['rows'] if r['passed']}
    cases = [c for c in original['cases'] if c['item']['id'] in admitted]
    files = [*ROOT.glob('*.py'), *ROOT.glob('*.sbatch'), ROOT/'PLAN.md', SOURCE/'manifest.json', SOURCE/'result.json']
    identities = dict(original['identities'], **guard['identities'])
    identities.update({str(p):sha(p) for p in files})
    save(ROOT/'manifest.json', dict(cases=cases, seeds=original['seeds'], identities=identities,
        reservation_supersedes=str(SOURCE), physical_attempts=0, model_calls=0, training_ready=False))
    rows = []
    for case in cases:
        name = case['item']['id']
        with (ROOT/(name+'.log')).open('x') as log:
            subprocess.run([sys.executable, '-B', str(ROOT/'one.py'), name],
                stdout=log, stderr=subprocess.STDOUT, check=True, timeout=900)
        rows.append(read(ROOT/'results'/(name+'.json')))
        print(dict(id=name, passed=rows[-1]['passed'], status=rows[-1]['status']), flush=True)
    assert all(sha(p) == h for p,h in identities.items())
    save(ROOT/'result.json', dict(rows=rows, physical_attempts=0, model_calls=0, training_ready=False,
        limitation='Requalification of previously admitted pilot conditions; not an unbiased distribution'))


if __name__ == '__main__':
    main()
