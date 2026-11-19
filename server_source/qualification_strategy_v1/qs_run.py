"""每个固定条件规划和独立审计各一个进程，无物理尝试。"""
import sys
import subprocess
from qs_common import ROOT, RUN, NAMES, read, save, sha, verify

TIMEOUT_SECONDS = 600


def main():
    manifest = verify(RUN/'manifest.json')
    rows = []
    for name in NAMES:
        for mode in ('probe', 'audit'):
            path = RUN/(name+'_'+mode+'.log')
            with path.open('x', encoding='utf-8') as stream:
                subprocess.run([sys.executable, '-B', str(ROOT/'qs_probe.py'), name, mode],
                    stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=TIMEOUT_SECONDS)
        result = verify(RUN/'audit'/name/'result.json')
        assert result['independently_reproduced']
        rows.append(result)
    verify(RUN/'manifest.json')
    paths = [p for p in RUN.rglob('*.json')]
    save(RUN/'result.json', dict(rows=rows, identities={str(p): sha(p) for p in paths},
        passed=True, newly_qualified=sum(r['top']['passed'] for r in rows),
        registered=len(manifest['cases']), physical_attempts=0, model_calls=0, training_updates=0))
    print(dict(passed=True, newly_qualified=sum(r['top']['passed'] for r in rows)), flush=True)


if __name__ == '__main__':
    main()
