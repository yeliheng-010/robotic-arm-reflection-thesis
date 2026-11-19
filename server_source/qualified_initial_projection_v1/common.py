"""新候选独立来源协议；旧快照和动力学授权均不修改。"""
import gzip
import importlib
import json
import os
from pathlib import Path
from qualified_initial_state_v1.common import XML, PARAMETERS, OLD, input_states
from qualified_initial_state_v1.common import load_all as load_parent
from qualified_closure_dynamics_v1.protocol import read, save, sha, require
from qualified_closure_dynamics_v3.guarded_imports import zero_motion
from qualified_closure_dynamics_v3.protocol import validate_runtime

ROOT = Path(__file__).resolve().parent
PROJECT, RUN, PREPARED = ROOT.parent, ROOT / 'run', ROOT / 'prepared'


def load_all():
    load_parent()
    for name in ('solver', 'projection', 'register', 'construct', 'audit'):
        importlib.import_module('qualified_initial_projection_v1.' + name)


def verify():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    manifest = read(PREPARED / 'manifest.json')
    for name, digest in manifest['identities'].items():
        require(sha(name) == digest, 'Frozen source changed: ' + name)
    with zero_motion() as counts:
        load_all()
        with gzip.open(PREPARED / 'runtime.json.gz', 'rt', encoding='utf-8') as stream:
            checked = validate_runtime(json.load(stream))
        require(not any(counts.values()), 'Unexpected construction/integration during imports')
    require(read(OLD / 'claim.json')['consumed'] == 1, 'Old physical claim changed')
    return dict(verified_identities=len(manifest['identities']), import_counts=counts, **checked)
