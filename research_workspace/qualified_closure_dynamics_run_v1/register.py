"""依据本次明确确认登记一次预算；不创建场景或执行动力学。"""
import os
from datetime import datetime, timezone
from pathlib import Path
from qualified_closure_dynamics_v1.protocol import ROOT as ENGINE, BUDGET, DIAGNOSTIC_ID, read, save, sha, require

ROOT = Path(__file__).resolve().parent
PREPARATION_SHA256 = '65b6d59264682dcf9b7bdc87f18844926cdedaba94ea33d3a97ddb8c1b8ce9ae'


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    require(not (ENGINE / 'authorization.json').exists(), 'Authorization already exists')
    require(not (ENGINE / 'run').exists(), 'Diagnostic already attempted')
    path = ENGINE / 'preparation_manifest.json'
    require(sha(path) == PREPARATION_SHA256, 'Prepared implementation changed')
    prepared = read(path)
    require(prepared['execution_authorized'] is False, 'Unexpected preparation state')
    require(prepared['proposed_budget'] == BUDGET, 'Budget mismatch')
    for name, digest in prepared['identities'].items():
        require(sha(name) == digest, 'Changed source: ' + name)
    auth = dict(execution_authorized=True, diagnostic_id=DIAGNOSTIC_ID, budget=BUDGET,
        preparation_sha256=PREPARATION_SHA256, identities=prepared['identities'],
        approval_reference='Current user accepted the immediately preceding recommendation: '
            'one isolated diagnostic, up to 500 setup and 1000 closure steps, stop on contact/failure, '
            'no retry, followed by one zero-integration evidence audit.',
        user_message='采取你的建议', registered_at_utc=datetime.now(timezone.utc).isoformat(),
        registration_job=os.environ['SLURM_JOB_ID'])
    save(ENGINE / 'authorization.json', auth)
    sources = {str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.sbatch', '.md')}
    save(ROOT / 'registration.json', dict(job=os.environ['SLURM_JOB_ID'], passed=True,
         verified_identities=len(prepared['identities']), sources=sources,
         authorization_sha256=sha(ENGINE / 'authorization.json'), budget=BUDGET,
         setup_steps=0, task_steps=0))
    print(dict(registered=True, identities=len(prepared['identities']), budget=BUDGET), flush=True)


if __name__ == '__main__':
    main()
