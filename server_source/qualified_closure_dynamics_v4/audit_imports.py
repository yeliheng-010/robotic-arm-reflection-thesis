"""相同GPU资源下的独立零积分导入审计。"""
import os
from qualified_closure_dynamics_v4.protocol import (
    PROJECT, PREPARED, read, save, sha, require, no_dynamics)
from qualified_closure_dynamics_v4.runtime import checked_imports


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    no_dynamics()
    checked = checked_imports()
    no_dynamics()
    require(read(PROJECT / 'qualified_closure_dynamics_v1/run/claim.json')['consumed'] == 1, 'Old claim changed')
    result = dict(passed=True, scope='gpu_real_imports_zero_motion', job=os.environ['SLURM_JOB_ID'],
        **checked, preparation_sha256=sha(PREPARED / 'manifest.json'),
        old_claim_preserved=True, execution_authorized=False, dynamics_validated=False)
    save(PREPARED / 'audit_result.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    main()
