"""以只读进程适配冻结审计器，不能重新执行诊断。"""
import os
from pathlib import Path
from qualified_closure_dynamics_v3.protocol import (
    ROOT as ENGINE, RUN, read, save, sha, require, verify_authorization)

ROOT = Path(__file__).resolve().parent


def verify_lineage():
    auth = verify_authorization(ENGINE / 'authorization.json')
    registration = read(ROOT / 'registration.json')
    require(registration['authorization_sha256'] == sha(ENGINE / 'authorization.json'), 'Authorization changed')
    for name, digest in registration['sources'].items():
        require(sha(name) == digest, 'Wrapper changed: ' + name)
    claim = read(RUN / 'claim.json')
    require(claim['consumed'] == 1 and claim['job'] == '6851', 'Diagnostic claim mismatch')
    require(claim['authorization_sha256'] == registration['authorization_sha256'], 'Claim binding mismatch')
    require(not (RUN / 'failure.json').exists(), 'Use failure evidence audit for incomplete run')
    result = read(RUN / 'result.json')
    require(result['error'] is None and result['uncertain_step'] is None, 'Incomplete trace')
    return len(auth['identities'])


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    save(ROOT / 'audit_attempt.json', dict(consumed=1, job=os.environ['SLURM_JOB_ID'],
        scope='saved_trajectory_only', source_sha256=sha(Path(__file__)),
        launcher_sha256=sha(ROOT / 'audit.sbatch')))
    try:
        count = verify_lineage()
        from qualified_closure_dynamics_v1 import audit
        audit.RUN = RUN
        audit.main()
        result = read(RUN / 'audit_result.json')
        save(ROOT / 'audit_summary.json', dict(passed=result['passed'], job=os.environ['SLURM_JOB_ID'],
            verified_identities=count, integration_steps=result['integration_steps'],
            task_steps=result['task_steps'], production_ready=False,
            audit_result_sha256=sha(RUN / 'audit_result.json')))
        print(read(ROOT / 'audit_summary.json'), flush=True)
    except Exception as error:
        save(ROOT / 'audit_failure.json', dict(passed=False, job=os.environ['SLURM_JOB_ID'],
            error=type(error).__name__ + ': ' + str(error), retry_allowed=False))
        raise


if __name__ == '__main__':
    main()
