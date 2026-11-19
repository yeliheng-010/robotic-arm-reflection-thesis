"""依据本次确认独立登记唯一v4轨迹预算，不创建场景。"""
import os
from datetime import datetime, timezone
from pathlib import Path
from qualified_closure_dynamics_v4.protocol import (
    ROOT as ENGINE, PREPARED, BUDGET, DIAGNOSTIC_ID, read, save, sha, require)

ROOT = Path(__file__).resolve().parent
PREPARATION_SHA256 = '66b01dbad123d36e07d55d318fa2167e28fbd89dd740650e5a373ed8dfcd37e9'


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    require(not (ENGINE / 'authorization.json').exists(), 'Authorization already exists')
    require(not (ENGINE / 'run').exists(), 'Diagnostic already attempted')
    require(sha(PREPARED / 'manifest.json') == PREPARATION_SHA256, 'Preparation changed')
    prepared = read(PREPARED / 'manifest.json')
    checks = {}
    for name in ('audit_result.json', 'entry_check.json'):
        audit = read(PREPARED / name)
        require(audit['passed'] is True, 'GPU check not passed')
        require(audit['preparation_sha256'] == PREPARATION_SHA256, 'Check binding mismatch')
        require(not any(audit['counts'].values()), 'Preparation attempted simulation')
        require(audit['gpu_profile'] == prepared['gpu_profile'], 'GPU profile mismatch')
        require(audit['verified_identities'] == len(prepared['identities']) == 8401, 'Identity count mismatch')
        checks[name] = sha(PREPARED / name)
    for name, digest in prepared['identities'].items():
        require(sha(name) == digest, 'Changed source: ' + name)
    auth = dict(execution_authorized=True, diagnostic_id=DIAGNOSTIC_ID, budget=BUDGET,
        preparation_sha256=PREPARATION_SHA256, identities=prepared['identities'],
        approval_reference='Current user accepted the immediately preceding recommendation: '
            'one isolated v4 diagnostic, up to 500 setup and 1000 closure steps, '
            'stop on contact/failure, no retry, then one zero-integration evidence audit.',
        user_message='采取你的建议', registered_at_utc=datetime.now(timezone.utc).isoformat(),
        registration_job=os.environ['SLURM_JOB_ID'])
    save(ENGINE / 'authorization.json', auth)
    sources = {str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.sbatch', '.md')}
    save(ROOT / 'registration.json', dict(job=os.environ['SLURM_JOB_ID'], passed=True,
        verified_identities=len(prepared['identities']), sources=sources, gpu_check_hashes=checks,
        authorization_sha256=sha(ENGINE / 'authorization.json'), budget=BUDGET,
        setup_steps=0, task_steps=0))
    print(dict(registered=True, identities=len(prepared['identities']), budget=BUDGET), flush=True)


if __name__ == '__main__':
    main()
