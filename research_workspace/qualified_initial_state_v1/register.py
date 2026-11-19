"""登记一次零积分诊断来源；不授权任何动力学。"""
import gzip
import json
import os
import sys
from qualified_initial_state_v1.common import (
    ROOT, PROJECT, PREPARED, RUN, XML, PARAMETERS, ORIGINAL, OLD, read, save, sha, require, load_all)
from qualified_closure_dynamics_v3 import provenance, distributions
from qualified_closure_dynamics_v3.preflight import project_binding
from qualified_closure_dynamics_v3.guarded_imports import zero_motion

OLD_AUTH_SHA = '7f9b7525b8ed38d19f9735c88cf56a4f4b0cb5df3675ce73a040ef341b41ee2d'
OLD_AUDIT_SHA = '99eb10a55009854df197628c5b639cacd86f6b09519b8c1a99adc52db1b11504'


def frozen():
    auth = PROJECT / 'qualified_closure_dynamics_v4/authorization.json'
    audit = PROJECT / 'qualified_closure_dynamics_run_v4/failure_audit.json'
    require(sha(auth) == OLD_AUTH_SHA and sha(audit) == OLD_AUDIT_SHA, 'Old evidence changed')
    identities = dict(read(auth)['identities'])
    identities.update(read(audit)['identities'])
    identities.update({str(auth): OLD_AUTH_SHA, str(audit): OLD_AUDIT_SHA})
    for path in (XML, PARAMETERS, ORIGINAL, OLD / 'initial_transform.npz'):
        require(str(path) in identities, 'Diagnostic input was not frozen: ' + str(path))
    for name, digest in identities.items():
        require(sha(name) == digest, 'Old input changed: ' + name)
    for path in ROOT.iterdir():
        if path.suffix in ('.py', '.md', '.sbatch'):
            identities[str(path)] = sha(path)
    return identities


def collect(identities):
    for _ in range(3):
        previous = set(sys.modules)
        snapshot = provenance.collect(dict(sys.modules), provenance.roots())
        snapshot['distributions'] = distributions.bind(snapshot)
        if previous == set(sys.modules):
            project_binding(snapshot, identities)
            snapshot['interpreter'] = provenance.interpreter()
            snapshot['allowed_entrypoints'] = {str(ROOT / name): sha(ROOT / name)
                for name in ('register.py', 'diagnose.py', 'audit.py')}
            snapshot['preparation_entrypoint'] = provenance.verify_entrypoint(
                sys.modules, snapshot['allowed_entrypoints'])
            return snapshot
    raise ValueError('Import metadata did not stabilize')


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    require(not PREPARED.exists() and not RUN.exists(), 'Already prepared')
    identities = frozen()
    with zero_motion() as counts:
        try:
            load_all()
            snapshot = collect(identities)
            require(not any(counts.values()), 'Unexpected construction/integration')
        except Exception as error:
            save(ROOT / ('registration_failure_' + os.environ['SLURM_JOB_ID'] + '.json'),
                 dict(error=type(error).__name__ + ': ' + str(error), counts=counts))
            raise
    PREPARED.mkdir(exist_ok=False)
    with (PREPARED / 'runtime.json.gz').open('xb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as stream:
            stream.write(json.dumps(snapshot, ensure_ascii=True, sort_keys=True).encode())
    identities.update({name: row['sha256'] for name, row in snapshot['files'].items()})
    for package in snapshot['distributions']['packages'].values():
        identities.update(package['identities'])
    identities[snapshot['interpreter']['executable']] = snapshot['interpreter']['sha256']
    identities[str(PREPARED / 'runtime.json.gz')] = sha(PREPARED / 'runtime.json.gz')
    save(PREPARED / 'manifest.json', dict(identities=identities, import_counts=counts,
        execution_authorized=False, integration_budget=0, job=os.environ['SLURM_JOB_ID'],
        modules=len(snapshot['modules']), files=len(snapshot['files'])))
    print(dict(registered=True, identities=len(identities), counts=counts), flush=True)


if __name__ == '__main__':
    main()
