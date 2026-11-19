"""独立审计后归档作业、源码、预算与输入/输出；不再生成。"""
import ast
import os
import subprocess
from qualified_prompt_checkpoint_v1.protocol import ROOT, PROJECT, RUN, read, save, sha, verify


def main():
    manifest = verify()
    assert read(RUN / 'audit_result.json')['passed']
    sources = list(ROOT.glob('*.py'))
    for path in sources:
        source = path.read_text(encoding='utf-8')
        assert len(source.splitlines()) <= 300, path
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.FunctionDef):
                assert node.end_lineno - node.lineno + 1 <= 50, (path, node.name)
    jobs = sorted({p.stem.rsplit('-', 1)[1] for p in ROOT.glob('*.log')})
    accounting = subprocess.run(['sacct', '-j', ','.join(jobs),
        '--format=JobID,State,ExitCode,Elapsed', '-n', '-P'], capture_output=True, text=True, check=True).stdout
    active = 'closeout-' + os.environ['SLURM_JOB_ID'] + '.log'
    identities = {str(p.relative_to(ROOT)): sha(p) for p in ROOT.rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts and p.name != active}
    save(RUN / 'delivery_inventory.json', dict(passed=True, identities=identities,
         frozen_identities=len(manifest['identities']), python_sources_checked=len(sources),
         job_accounting=accounting, findings=read(RUN / 'result.json'),
         original_claim_sha256=sha(PROJECT / 'qualified_execution_v1/run/attempt_claim.json')))
    print(dict(passed=True, files=len(identities), findings=read(RUN / 'result.json')), flush=True)


if __name__ == '__main__':
    main()
