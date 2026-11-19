"""实际旧失败仍拒绝，旧通过结果等价；不新增物理尝试。"""
import ast
import os
import subprocess
import sys
from iv3_audit import ROOT, BASE, inspect
from iv3_geometry import ReconstructionMismatch
from collection_common import PHYSICS, verify, save, sha
from ig_audit import contact_evidence

MAX_FILE_LINES = 300
MAX_FUNCTION_LINES = 50


def check_sources():
    for path in ROOT.glob('*.py'):
        source = path.read_text(encoding='utf-8')
        assert len(source.splitlines()) <= MAX_FILE_LINES
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno-node.lineno+1 <= MAX_FUNCTION_LINES
    for name in ('iv3_jobs', 'iv3_merge', 'iv3_next'):
        command = f'import {name} as m; from pathlib import Path; assert Path(m.__file__).resolve()==Path({str(ROOT / (name+".py"))!r}); print(m.__file__)'
        subprocess.run([sys.executable, '-B', '-c', command], check=True, cwd=ROOT)


def actual_checks():
    cases = {c['item']['id']: c for c in verify(PHYSICS / 'manifest.json')['cases']}
    failed = cases['R1_964194_varied_noisy']
    result, contacts = contact_evidence(failed)
    assert result['attempts'] == 7 and not any(r['self_contact_samples'] for r in contacts)
    try:
        inspect(failed)
    except ReconstructionMismatch as error:
        evidence = error.evidence
    else:
        raise AssertionError('Known geometry mismatch was incorrectly accepted')
    prior = verify(PHYSICS / 'audits/R0_964194_varied_noisy.json')['row']
    replayed = inspect(cases[prior['id']])
    assert prior == replayed
    return dict(rejected_case=failed['item']['id'], evidence=evidence, contacts=contacts,
        prior_case=prior['id'], prior_exact_equal=True, physical_attempts=0, model_calls=0)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    verify(BASE / 'source_manifest.json')
    check_sources()
    result = actual_checks()
    save(ROOT / 'verification' / ('job_'+os.environ['SLURM_JOB_ID']+'.json'), result)
    paths = [*ROOT.glob('*.py'), *ROOT.glob('*.sbatch'), ROOT / 'PLAN.md', BASE / 'source_manifest.json']
    assert not (ROOT / 'source_manifest.json').exists()
    save(ROOT / 'source_manifest.json', dict(identities={str(p): sha(p) for p in paths},
        physical_attempts=0, model_calls=0, training_updates=0))
    print('Known mismatch rejected, prior accepted case exactly equal, sources frozen', flush=True)


if __name__ == '__main__':
    main()
