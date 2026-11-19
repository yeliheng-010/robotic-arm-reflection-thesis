"""冻结三个条件和候选版本，规划/审计分进程，不新增物理尝试。"""
import ast
import sys
import subprocess
from cp_common import ROOT, SOURCE, RUN, read, save, sha, verify

TIMEOUT_SECONDS = 600


def prepare():
    assert not RUN.exists()
    source = verify(SOURCE/'manifest.json')
    result = verify(SOURCE/'result.json')
    assert result['passed'] and result['newly_qualified'] == 0
    cases = [dict(name=r['id'], original=r) for r in result['rows']]
    identities = dict(source['identities'], **result['identities'])
    paths = [SOURCE/'manifest.json', SOURCE/'result.json', *ROOT.glob('*.py'), *ROOT.glob('*.sh'), *ROOT.glob('*.sbatch')]
    for path in ROOT.glob('*.py'):
        code = path.read_text()
        assert len(code.splitlines()) <= 300
        for node in ast.walk(ast.parse(code)):
            if isinstance(node, ast.FunctionDef):
                assert node.end_lineno-node.lineno+1 <= 50
    identities.update({str(p): sha(p) for p in paths})
    save(RUN/'manifest.json', dict(cases=cases, identities=identities, max_candidates=30,
        physical_attempts=0, model_calls=0, training_updates=0))
    return cases


def main():
    rows = []
    for case in prepare():
        name = case['name']
        for mode in ('probe','audit'):
            with (RUN/(name+'_'+mode+'.log')).open('x') as stream:
                subprocess.run([sys.executable, '-B', str(ROOT/'cp_probe.py'), name, mode],
                    stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=TIMEOUT_SECONDS)
        row = verify(RUN/'audit'/name/'result.json')
        assert row['independently_reproduced']
        rows.append(row)
    verify(RUN/'manifest.json')
    paths = [p for p in RUN.rglob('*.json')]
    save(RUN/'result.json', dict(passed=True, rows=rows, qualified=sum(r['qualified'] for r in rows),
        physical_attempts=0, model_calls=0, identities={str(p): sha(p) for p in paths}))
    print(dict(passed=True, qualified=sum(r['qualified'] for r in rows)), flush=True)


if __name__ == '__main__':
    main()
