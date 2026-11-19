"""登记用户确认的唯一v3诊断预算，不构造场景。"""
import os
from datetime import datetime, timezone
from pathlib import Path
from qualified_closure_dynamics_v3.protocol import (
    ROOT as ENGINE, PREPARED, BUDGET, DIAGNOSTIC_ID, read, save, sha, require)

ROOT = Path(__file__).resolve().parent
PREPARATION_SHA256 = 'fa4304f35f26181fa3c32f6c2330407047f094c0cb6e8dc159eef8e719102f89'


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    require(not (ENGINE / 'authorization.json').exists(), 'Authorization already exists')
    require(not (ENGINE / 'run').exists(), 'Diagnostic already attempted')
    require(sha(PREPARED / 'manifest.json') == PREPARATION_SHA256, 'Preparation changed')
    prepared, audit = read(PREPARED / 'manifest.json'), read(PREPARED / 'audit_result.json')
    require(audit['passed'] is True, 'Preparation audit not passed')
    require(audit['preparation_sha256'] == PREPARATION_SHA256, 'Audit binding mismatch')
    require(not any(audit['counts'].values()), 'Preparation attempted simulation')
    require(audit['verified_identities'] == len(prepared['identities']) == 8380, 'Identity count mismatch')
    for name, digest in prepared['identities'].items():
        require(sha(name) == digest, 'Changed source: ' + name)
    auth = dict(execution_authorized=True, diagnostic_id=DIAGNOSTIC_ID, budget=BUDGET,
        preparation_sha256=PREPARATION_SHA256, identities=prepared['identities'],
        approval_reference='Current user accepted the immediately preceding recommendation: '
            'one isolated v3 diagnostic, up to 500 setup and 1000 closure steps, '
            'stop on contact/failure, no retry, then one zero-integration evidence audit.',
        user_message='采取你的建议', registered_at_utc=datetime.now(timezone.utc).isoformat(),
        registration_job=os.environ['SLURM_JOB_ID'])
    save(ENGINE / 'authorization.json', auth)
    sources = {str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.sbatch', '.md')}
    save(ROOT / 'registration.json', dict(job=os.environ['SLURM_JOB_ID'], passed=True,
        verified_identities=len(prepared['identities']), sources=sources,
        preparation_audit_sha256=sha(PREPARED / 'audit_result.json'),
        authorization_sha256=sha(ENGINE / 'authorization.json'), budget=BUDGET,
        setup_steps=0, task_steps=0))
    print(dict(registered=True, identities=len(prepared['identities']), budget=BUDGET), flush=True)


if __name__ == '__main__':
    main()
