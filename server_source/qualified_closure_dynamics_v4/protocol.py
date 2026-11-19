"""v4独立准备与授权协议；本轮不发放动力学授权。"""
import gzip
import json
import os
from pathlib import Path
from qualified_closure_dynamics_v1.protocol import BUDGET, sha, read, save, require
from qualified_closure_dynamics_v3.protocol import validate_runtime

ROOT = Path(__file__).resolve().parent
PROJECT, PREPARED, RUN = ROOT.parent, ROOT / 'prepared', ROOT / 'run'
DIAGNOSTIC_ID = 'qualified_closure_dynamics_v4-978505'


def read_snapshot():
    with gzip.open(PREPARED / 'runtime.json.gz', 'rt', encoding='utf-8') as stream:
        return json.load(stream)


def no_dynamics():
    require(not RUN.exists() and not (ROOT / 'authorization.json').exists(), 'Unexpected dynamics state')


def verify_preparation():
    manifest = read(PREPARED / 'manifest.json')
    require(manifest['execution_authorized'] is False, 'Preparation cannot authorize dynamics')
    for name, digest in manifest['identities'].items():
        require(sha(name) == digest, 'Frozen source changed: ' + name)
    return manifest


def verify_authorization(path):
    auth = read(path)
    manifest = verify_preparation()
    require(auth.get('execution_authorized') is True, 'No v4 dynamics authorization')
    require(auth.get('diagnostic_id') == DIAGNOSTIC_ID, 'Wrong diagnostic version')
    require(auth.get('budget') == BUDGET, 'Wrong budget')
    require(all(type(v) is int for v in auth['budget'].values()), 'Integer budget required')
    require(bool(auth.get('approval_reference')), 'Approval reference required')
    require(auth.get('preparation_sha256') == sha(PREPARED / 'manifest.json'), 'Preparation changed')
    require(auth.get('identities') == manifest['identities'], 'Identity set mismatch')
    return auth


def consume(auth, folder):
    require(auth['diagnostic_id'] == DIAGNOSTIC_ID, 'Cannot reuse old claim')
    save(folder / 'claim.json', dict(consumed=1, diagnostic_id=DIAGNOSTIC_ID,
         job=os.environ.get('SLURM_JOB_ID'), authorization_sha256=sha(ROOT / 'authorization.json')))
