"""--verify只执行零步共享路径；缺独立授权禁止真实执行。"""
import os
import sys
from qualified_closure_mjb_v1.protocol import (
    ROOT, RUN, PREPARED, VERIFIED, read, save, sha, require,
    check_identities, validate_authorization, consume)


def authorization():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    auth = read(ROOT/'authorization.json')
    ready = read(ROOT/'readiness.json')
    require(ready['entrypoint_ready'] and ready['execution_authorized'] is False, 'Entry not reviewed')
    validate_authorization(auth, expected=ready['identities'], preparation_digest=sha(ROOT/'readiness.json'))
    check_identities(ready['identities'])
    return auth, ready


def execute_authorized(authorization_record):
    from qualified_closure_mjb_v1.runtime import checked_imports
    from qualified_closure_mjb_v1.pipeline import run
    auth, ready = authorization_record
    imports = checked_imports()
    check_identities(ready['identities'])
    consume(auth, RUN, expected=ready['identities'], preparation_digest=sha(ROOT/'readiness.json'))
    run(RUN, mode='execution', imports=imports)


def verify_entry():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    require(not RUN.exists() and not (ROOT/'authorization.json').exists(), 'Unexpected dynamics registration')
    prepared = read(PREPARED/'manifest.json')
    require(prepared['passed'] and prepared['execution_authorized'] is False, 'Not prepared')
    check_identities(prepared['identities'])
    from qualified_closure_mjb_v1.runtime import checked_imports
    from qualified_closure_mjb_v1.pipeline import run
    imports = checked_imports()
    require(imports['gpu_profile'] == prepared['gpu_profile'], 'Prepared GPU differs')
    save(VERIFIED/'claim.json', dict(kind='entry_verification', consumed=1,
         dynamics_budget_consumed=0, job=os.environ['SLURM_JOB_ID']))
    run(VERIFIED, mode='verification', imports=imports)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args == ['--verify']:
        verify_entry()
    else:
        require(not args, 'Unknown entry arguments')
        execute_authorized(authorization())


if __name__ == '__main__':
    main()
