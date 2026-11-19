"""只汇总测试/零步入口/独立审计证据，不生成执行授权。"""
import os
from qualified_closure_mjb_v1.protocol import (
    ROOT, RUN, PREPARED, VERIFIED, read, save, sha, require, check_identities)


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    require(not RUN.exists() and not (ROOT/'authorization.json').exists(), 'Unexpected dynamics registration')
    prepared, execution, audit = (read(path) for path in
        (PREPARED/'manifest.json', VERIFIED/'result.json', VERIFIED/'audit_result.json'))
    require(prepared['passed'] and audit['passed'] and audit['verification_only'], 'Checks incomplete')
    require(execution['mode'] == 'verification' and execution['reasons'] == ['verification_only'], 'Initial gate rejected')
    require(execution['completed_steps'] == audit['task_steps'] == 0 and execution['error'] is None, 'Not zero step')
    require(not any(prepared['counts'].values()), 'Preparation simulation request')
    for result in (execution, audit):
        require(result['counts']['integration'] == result['counts']['native_returns'] == 0, 'Integration request')
        require(result['counts']['binary_load'] == 1, 'Unexpected model load count')
        require(all(result['counts'][k] == 0 for k in
                    ('setup_steps', 'forbidden', 'reset', 'compile', 'rendering', 'planning', 'optimizer', 'close')),
                'Forbidden action')
    identities = dict(prepared['identities'])
    check_identities(identities)
    for name, digest in read(VERIFIED/'primary_inventory.json').items():
        require(sha(VERIFIED/name) == digest, 'Changed original verification evidence')
    for folder in (PREPARED, VERIFIED):
        for path in folder.iterdir():
            if path.is_file():
                identities[str(path)] = sha(path)
    save(ROOT/'readiness.json', dict(entrypoint_ready=True, execution_authorized=False,
         dynamics_budget_consumed=0, job=os.environ['SLURM_JOB_ID'], identities=identities,
         preparation_job=prepared['job'], verification_job=execution['job'], audit_job=audit['job'],
         production_ready=False, dynamics_validated=False))
    print(dict(entrypoint_ready=True, execution_authorized=False, identities=len(identities)), flush=True)


if __name__ == '__main__':
    main()
