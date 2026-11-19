"""合成检查后重放实际失败与既有通过样例；不重新执行物理。"""
import ast
import os
import subprocess
import sys
from pathlib import Path
from collection_common import PHYSICS, read, save, sha, verify
from ig_audit import inspect, contact_evidence
from ig_policy import audit_disposition

ROOT = Path(__file__).resolve().parent
MAX_FUNCTION_LINES = 50
MAX_FILE_LINES = 300


def actual_checks():
    manifest = verify(PHYSICS / 'manifest.json')
    cases = {c['item']['id']: c for c in manifest['cases']}
    repaired = inspect(cases['R0_964160_varied_noisy'])
    assert repaired['attempts'] == 7
    original = verify(PHYSICS / 'audits/R0_964135_varied_noisy.json')['row']
    replayed = inspect(cases[original['id']])
    assert original['attempts'] == replayed['attempts'] and original['methods'] == replayed['methods']
    assert {r['path']: r['contact'] for r in original['physical']} == {
        r['path']: r['contact'] for r in replayed['physical']}
    result, contacts = contact_evidence(cases['R0_964143_varied_noisy'])
    assert result['attempts'] == 4
    assert audit_disposition([r['self_contact_samples'] for r in contacts]) == 'quarantine'
    return dict(repaired_case=repaired, rejected_case_contacts=contacts,
        prior_case_id=original['id'], prior_methods_equal=True, physical_attempts=0, model_calls=0)


def check_sources():
    for path in ROOT.glob('*.py'):
        source = path.read_text(encoding='utf-8')
        assert len(source.splitlines()) <= MAX_FILE_LINES
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno - node.lineno + 1 <= MAX_FUNCTION_LINES
    for module in ('ig_jobs', 'ig_merge', 'ig_next', 'ig_execution'):
        command = f'import {module} as m; from pathlib import Path; assert Path(m.__file__).resolve()==Path({str(ROOT / (module+".py"))!r}); print(m.__file__)'
        subprocess.run([sys.executable, '-B', '-c', command], check=True, cwd=ROOT)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    check_sources()
    result = actual_checks()
    save(ROOT / 'verification' / ('job_'+os.environ['SLURM_JOB_ID']+'.json'), result)
    paths = [*ROOT.glob('*.py'), *ROOT.glob('*.sbatch'), ROOT / 'PLAN.md']
    save(ROOT / 'source_manifest.json', dict(identities={str(p): sha(p) for p in paths},
        physical_attempts=0, model_calls=0, training_updates=0))
    print('Actual failed geometry repaired; unsafe case quarantined; prior case audit retained; source frozen', flush=True)


if __name__ == '__main__':
    main()
