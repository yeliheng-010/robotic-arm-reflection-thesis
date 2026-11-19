"""新证据阶段排他登记，零运动规划与独立重建。"""
import ast
import sys
import subprocess
from qs_common import ROOT, RUN as PROBE, NAMES, read, save, sha, verify

RUN = ROOT/'actual'
TIMEOUT_SECONDS = 600


def main():
    assert not RUN.exists()
    source, result = verify(PROBE/'manifest.json'), verify(PROBE/'result.json')
    assert result['passed'] and result['newly_qualified'] == 0
    paths = [PROBE/'manifest.json', PROBE/'result.json', *ROOT.glob('qa_*.py'), ROOT/'actual.sbatch']
    for path in ROOT.glob('qa_*.py'):
        code = path.read_text()
        assert len(code.splitlines()) <= 300
        for node in ast.walk(ast.parse(code)):
            if isinstance(node, ast.FunctionDef):
                assert node.end_lineno-node.lineno+1 <= 50
    identities = dict(source['identities'], **result['identities'])
    identities.update({str(p): sha(p) for p in paths})
    save(RUN/'manifest.json', dict(identities=identities, names=list(NAMES),
        max_sensing_sessions=3, max_task_motion_calls=0, physical_attempts=0, model_calls=0))
    rows = []
    for name in NAMES:
        for script in ('qa_worker.py', 'qa_audit.py'):
            with (RUN/(name+'_'+script+'.log')).open('x') as stream:
                subprocess.run([sys.executable, '-B', str(ROOT/script), name],
                    stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=TIMEOUT_SECONDS)
        row = verify(RUN/'audits'/(name+'.json'))
        rows.append(dict(row, id=name))
    verify(RUN/'manifest.json')
    paths = [p for p in RUN.rglob('*.json')]
    save(RUN/'result.json', dict(passed=True, rows=rows, newly_qualified=sum(r['qualified'] for r in rows),
        identities={str(p): sha(p) for p in paths}, physical_attempts=0, model_calls=0))
    print(dict(passed=True, newly_qualified=sum(r['qualified'] for r in rows)), flush=True)


if __name__ == '__main__':
    main()
