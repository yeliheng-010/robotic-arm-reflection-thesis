"""冻结方案、原快照与投影器，不登记动力学预算。"""
import gzip
import json
import os
import sys
from qualified_initial_projection_v1.common import (
    ROOT, PROJECT, RUN, PREPARED, read, save, sha, require, load_all)
from qualified_closure_dynamics_v3 import provenance, distributions
from qualified_closure_dynamics_v3.preflight import project_binding
from qualified_closure_dynamics_v3.guarded_imports import zero_motion

PARENT_SHA = '9545736e94572867be471edce589323c87aa4e712370d5e02479b8eab06bb6a0'
AUDIT_SHA = '59d25dde2818f876a2a80a1feae351d9955ced098ae1894d29e940e8ada1b8c3'


def frozen():
    parent = PROJECT / 'qualified_initial_state_v1'
    prepared, audit = parent / 'prepared/manifest.json', parent / 'run/audit_result.json'
    require(sha(prepared) == PARENT_SHA and sha(audit) == AUDIT_SHA, 'Parent evidence changed')
    identities = dict(read(prepared)['identities'])
    require(read(audit)['passed'], 'Parent audit did not pass')
    require(sha(parent / 'run/result.json') == read(audit)['result_sha256'], 'Parent result changed')
    for name, digest in read(parent / 'run/inventory.json').items():
        identities[str(parent / 'run' / name)] = digest
    identities.update({str(prepared): PARENT_SHA, str(audit): AUDIT_SHA})
    identities[str(parent / 'run/inventory.json')] = sha(parent / 'run/inventory.json')
    for name, digest in identities.items():
        require(sha(name) == digest, 'Old source changed: ' + name)
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
                for name in ('register.py', 'construct.py', 'audit.py')}
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
