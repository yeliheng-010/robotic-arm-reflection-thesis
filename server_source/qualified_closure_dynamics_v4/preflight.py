"""GPU实际导入登记；禁止场景、积分、授权与claim。"""
import gzip
import json
import os
import sys
from qualified_closure_dynamics_v3 import provenance, distributions
from qualified_closure_dynamics_v3.preflight import project_binding
from qualified_closure_dynamics_v3.guarded_imports import zero_motion
from qualified_closure_dynamics_v4.protocol import (
    ROOT, PROJECT, PREPARED, sha, read, save, require, no_dynamics)
from qualified_closure_dynamics_v4.runtime import load_runtime, gpu_profile

V3_PREPARATION_SHA = 'fa4304f35f26181fa3c32f6c2330407047f094c0cb6e8dc159eef8e719102f89'
V3_AUTHORIZATION_SHA = 'e506a24fb887f085c66fb24eed83a0d6d2c1d5e25019a1ee56ca8bb2a0e65e1d'


def frozen_inputs():
    parent = PROJECT / 'qualified_closure_dynamics_v3'
    manifest = parent / 'prepared/manifest.json'
    require(sha(manifest) == V3_PREPARATION_SHA, 'Frozen v3 preparation changed')
    require(sha(parent / 'authorization.json') == V3_AUTHORIZATION_SHA, 'Frozen v3 authorization changed')
    identities = dict(read(manifest)['identities'])
    identities[str(manifest)] = V3_PREPARATION_SHA
    identities[str(parent / 'authorization.json')] = V3_AUTHORIZATION_SHA
    audit = PROJECT / 'qualified_closure_dynamics_run_v3/failure_audit.json'
    require(read(audit)['passed'] and read(audit)['new_claim_consumed'] == 0, 'Unexpected old audit')
    identities.update(read(audit)['identities'])
    identities[str(audit)] = sha(audit)
    require(not (parent / 'run').exists(), 'Old v3 unexpectedly retried')
    for name, digest in identities.items():
        require(sha(name) == digest, 'Frozen source changed: ' + name)
    for path in ROOT.iterdir():
        if path.suffix in ('.py', '.md', '.sbatch'):
            identities[str(path)] = sha(path)
    return identities


def collect_runtime(identities, profile):
    boundaries = provenance.roots()
    for _ in range(3):
        before = set(sys.modules)
        snapshot = provenance.collect(dict(sys.modules), boundaries)
        snapshot['distributions'] = distributions.bind(snapshot)
        if before == set(sys.modules):
            project_binding(snapshot, identities)
            snapshot['interpreter'] = provenance.interpreter()
            snapshot['gpu_profile'] = profile
            snapshot['allowed_entrypoints'] = {str(ROOT / name): sha(ROOT / name)
                for name in ('preflight.py', 'audit_imports.py', 'entry.py')}
            snapshot['preparation_entrypoint'] = provenance.verify_entrypoint(
                sys.modules, snapshot['allowed_entrypoints'])
            return snapshot
    raise ValueError('Import metadata did not stabilize within three read-only passes')


def persist(snapshot, identities, counts):
    PREPARED.mkdir(exist_ok=False)
    with (PREPARED / 'runtime.json.gz').open('xb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as stream:
            stream.write(json.dumps(snapshot, ensure_ascii=True, sort_keys=True).encode())
    identities.update({name: row['sha256'] for name, row in snapshot['files'].items()})
    identities[snapshot['interpreter']['executable']] = snapshot['interpreter']['sha256']
    for package in snapshot['distributions']['packages'].values():
        identities.update(package['identities'])
    identities[str(PREPARED / 'runtime.json.gz')] = sha(PREPARED / 'runtime.json.gz')
    result = dict(identities=identities, execution_authorized=False,
        runtime_sha256=sha(PREPARED / 'runtime.json.gz'), import_counts=counts,
        gpu_profile=snapshot['gpu_profile'], modules=len(snapshot['modules']), files=len(snapshot['files']),
        packages=len(snapshot['distributions']['packages']), job=os.environ['SLURM_JOB_ID'])
    save(PREPARED / 'manifest.json', result)
    print({key: value for key, value in result.items() if key != 'identities'}, flush=True)


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    no_dynamics()
    identities = frozen_inputs()
    with zero_motion() as counts:
        try:
            load_runtime()
            snapshot = collect_runtime(identities, gpu_profile())
            require(not any(counts.values()), 'Simulation attempted during preparation')
        except Exception as error:
            save(ROOT / ('failed_preflight_' + os.environ['SLURM_JOB_ID'] + '.json'),
                 dict(error=type(error).__name__ + ': ' + str(error), counts=counts))
            raise
    persist(snapshot, identities, counts)


if __name__ == '__main__':
    main()
