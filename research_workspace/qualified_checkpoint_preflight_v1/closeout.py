"""归档预算、预检拒绝/通过阶段、状态隔离与作业状态。"""
import ast
import os
import subprocess
from qualified_checkpoint_preflight_v1.protocol import ROOT, PROJECT, RUN, read, save, sha, verify


def main():
    manifest = verify()
    assert read(RUN / 'audit_result.json')['passed']
    result = read(RUN / 'result.json')
    assert result['model_calls'] == result['physical_attempts'] == result['training_runs'] == 0
    assert result['preflight_sessions'] == 1 and not result['physical_registered']
    assert read(RUN / 'audit_claim.json')['consumed'] == read(RUN / 'preflight_claim.json')['consumed'] == 1
    files = list(ROOT.glob('*.py'))
    for path in files:
        source = path.read_text(encoding='utf-8')
        assert len(source.splitlines()) <= 300
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.FunctionDef):
                assert node.end_lineno - node.lineno + 1 <= 50, (path, node.name)
    jobs = sorted({path.stem.rsplit('-', 1)[1] for path in ROOT.glob('*.log')})
    accounting = subprocess.run(['sacct', '-j', ','.join(jobs), '--format=JobID,State,ExitCode,Elapsed', '-n', '-P'],
                                check=True, capture_output=True, text=True).stdout
    active = 'closeout-' + os.environ['SLURM_JOB_ID'] + '.log'
    identities = {str(p.relative_to(ROOT)): sha(p) for p in ROOT.rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts and p.name != active}
    save(RUN / 'delivery_inventory.json', dict(passed=True, result=result, identities=identities,
         frozen_identities=len(manifest['identities']), python_sources_checked=len(files), job_accounting=accounting,
         original_claim_sha256=sha(PROJECT / 'qualified_execution_v1/run/attempt_claim.json')))
    print(dict(passed=True, files=len(identities), result=result), flush=True)


if __name__ == '__main__':
    main()
