"""v2独立授权；本轮只准备来源，不创建授权或轨迹claim。"""
import gzip
import json
import os
from pathlib import Path
from qualified_closure_dynamics_v1.protocol import BUDGET, sha, read, save, require

ROOT = Path(__file__).resolve().parent
PROJECT, PREPARED, RUN = ROOT.parent, ROOT / 'prepared', ROOT / 'run'
DIAGNOSTIC_ID = 'qualified_closure_dynamics_v3-978505'


def read_snapshot():
    with gzip.open(PREPARED / 'runtime.json.gz', 'rt', encoding='utf-8') as stream:
        return json.load(stream)


def verify_authorization(path):
    auth = read(path)
    manifest = read(PREPARED / 'manifest.json')
    require(auth.get('execution_authorized') is True, 'No v2 dynamics authorization')
    require(auth.get('diagnostic_id') == DIAGNOSTIC_ID, 'Wrong diagnostic version')
    require(auth.get('budget') == BUDGET, 'Wrong budget')
    require(all(type(v) is int for v in auth['budget'].values()), 'Integer budget required')
    require(bool(auth.get('approval_reference')), 'Approval reference required')
    require(auth.get('preparation_sha256') == sha(PREPARED / 'manifest.json'), 'Preparation changed')
    require(auth.get('identities') == manifest['identities'], 'Identity set mismatch')
    for name, digest in auth['identities'].items():
        require(sha(name) == digest, 'Source changed: ' + name)
    return auth


def consume(auth, folder):
    require(auth['diagnostic_id'] == DIAGNOSTIC_ID, 'Cannot reuse v1 claim')
    save(folder / 'claim.json', dict(consumed=1, diagnostic_id=DIAGNOSTIC_ID,
         job=os.environ.get('SLURM_JOB_ID'), authorization_sha256=sha(ROOT / 'authorization.json')))


def validate_runtime(expected):
    from qualified_closure_dynamics_v3 import provenance, distributions
    import sys
    require(provenance.roots() == expected['roots'], 'Interpreter source roots changed')
    require(provenance.interpreter() == expected['interpreter'], 'Interpreter changed')
    provenance.verify_files(expected)
    distributions.verify(expected['distributions'])
    current = provenance.collect(dict(sys.modules), expected['roots'])
    for name, row in current['files'].items():
        require(expected['files'].get(name) == row, 'New or changed imported file: ' + name)
    for name, row in current['modules'].items():
        require(expected['modules'].get(name) == row, 'New or changed imported module: ' + name)
    return dict(modules=len(current['modules']), files=len(current['files']))
