"""独立进程核验真实运行导入集合，禁止模型构造和积分。"""
import os
from qualified_closure_dynamics_v3.protocol import (
    ROOT, PROJECT, PREPARED, RUN, read, save, sha, require, read_snapshot, validate_runtime)
from qualified_closure_dynamics_v3.guarded_imports import zero_motion, load_runtime


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    require(not RUN.exists() and not (ROOT / 'authorization.json').exists(), 'Unexpected dynamics state')
    manifest = read(PREPARED / 'manifest.json')
    for name, digest in manifest['identities'].items():
        require(sha(name) == digest, 'Frozen source changed: ' + name)
    with zero_motion() as counts:
        load_runtime()
        snapshot = read_snapshot()
        checked = validate_runtime(snapshot)
        require(not any(counts.values()), 'Attempted simulation in independent audit')
    require(read(PROJECT / 'qualified_closure_dynamics_v1/run/claim.json')['consumed'] == 1, 'Old claim changed')
    dependency = snapshot['modules']['_distutils_hack']['file']
    detail = dict(path=dependency, source=snapshot['files'][dependency],
                  owner=snapshot['distributions']['files'][dependency])
    require(detail['source']['category'] == 'dependency', 'Regression not fixed')
    save(PREPARED / 'audit_result.json', dict(passed=True, scope='real_imports_zero_motion',
         job=os.environ['SLURM_JOB_ID'], counts=counts, **checked,
         verified_identities=len(manifest['identities']), regression_dependency=detail,
         preparation_sha256=sha(PREPARED / 'manifest.json'),
         old_claim_preserved=True, execution_authorized=False, dynamics_validated=False))
    print(dict(passed=True, **checked, counts=counts, execution_authorized=False), flush=True)


if __name__ == '__main__':
    main()
