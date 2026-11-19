"""先完成真实导入来源登记；场景/积分/授权/轨迹claim均禁止。"""
import ast
import gzip
import json
import os
import sys
from pathlib import Path
from qualified_closure_dynamics_v2.protocol import ROOT, PROJECT, PREPARED, RUN, sha, read, save, require
from qualified_closure_dynamics_v2 import provenance, distributions
from qualified_closure_dynamics_v2.guarded_imports import zero_motion, load_runtime

OLD_PREPARATION_SHA = '65b6d59264682dcf9b7bdc87f18844926cdedaba94ea33d3a97ddb8c1b8ce9ae'


def frozen_inputs():
    parent = PROJECT / 'qualified_closure_dynamics_v1'
    require(sha(parent / 'preparation_manifest.json') == OLD_PREPARATION_SHA, 'Old preparation changed')
    identities = dict(read(parent / 'preparation_manifest.json')['identities'])
    failure_audit = read(PROJECT / 'qualified_closure_dynamics_run_v1/failure_audit.json')
    identities.update(failure_audit['identities'])
    require(read(parent / 'run/claim.json')['consumed'] == 1, 'Old claim changed')
    for name, digest in identities.items():
        require(sha(name) == digest, 'Frozen source changed: ' + name)
    from qualified_closure_dynamics_v2.source_review import load
    supplemental = ROOT / 'reviewed_sources.json'
    identities.update(load(supplemental, PROJECT))
    identities[str(supplemental)] = sha(supplemental)
    for path in ROOT.iterdir():
        if path.suffix in ('.py', '.md', '.sbatch'):
            identities[str(path)] = sha(path)
    return identities


def project_binding(snapshot, identities):
    caches = {row['cached']: row['file'] for row in snapshot['modules'].values() if 'cached' in row}
    for name, row in snapshot['files'].items():
        if row['category'] != 'project':
            continue
        if name in caches:
            require(caches[name] in identities, 'Unbound project bytecode source')
        else:
            require(identities.get(name) == row['sha256'], 'Unbound project source: ' + name)


def collect_runtime(identities):
    boundaries = provenance.roots()
    for _ in range(3):
        before = set(sys.modules)
        snapshot = provenance.collect(dict(sys.modules), boundaries)
        snapshot['distributions'] = distributions.bind(snapshot)
        if before == set(sys.modules):
            project_binding(snapshot, identities)
            snapshot['interpreter'] = provenance.interpreter()
            return snapshot
    raise ValueError('Import metadata did not stabilize within three read-only passes')


def source_checks():
    for path in ROOT.glob('*.py'):
        text = path.read_text(encoding='utf-8')
        require(len(text.splitlines()) <= 300, 'Source too long')
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.FunctionDef):
                require(node.end_lineno - node.lineno + 1 <= 50, 'Function too long: ' + node.name)


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    require(not (ROOT / 'authorization.json').exists() and not RUN.exists(), 'No dynamics in preparation')
    source_checks()
    identities = frozen_inputs()
    with zero_motion() as counts:
        try:
            load_runtime()
            snapshot = collect_runtime(identities)
            require(not any(counts.values()), 'Attempted simulation during import')
        except Exception as error:
            save(ROOT / ('failed_preflight_' + os.environ['SLURM_JOB_ID'] + '.json'),
                 dict(error=type(error).__name__ + ': ' + str(error), counts=counts))
            raise
    PREPARED.mkdir(exist_ok=False)
    with (PREPARED / 'runtime.json.gz').open('xb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as stream:
            stream.write(json.dumps(snapshot, ensure_ascii=True, sort_keys=True).encode())
    identities.update({name: row['sha256'] for name, row in snapshot['files'].items()})
    identities[snapshot['interpreter']['executable']] = snapshot['interpreter']['sha256']
    for package in snapshot['distributions']['packages'].values():
        identities.update(package['identities'])
    identities[str(PREPARED / 'runtime.json.gz')] = sha(PREPARED / 'runtime.json.gz')
    save(PREPARED / 'manifest.json', dict(identities=identities, execution_authorized=False,
         runtime_sha256=sha(PREPARED / 'runtime.json.gz'), import_counts=counts,
         modules=len(snapshot['modules']), files=len(snapshot['files']),
         packages=len(snapshot['distributions']['packages']), job=os.environ['SLURM_JOB_ID']))
    print(dict(prepared=True, identities=len(identities), modules=len(snapshot['modules']),
               files=len(snapshot['files']), packages=len(snapshot['distributions']['packages']),
               counts=counts, execution_authorized=False), flush=True)


if __name__ == '__main__':
    main()
