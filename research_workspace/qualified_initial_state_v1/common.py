"""冻结来源、已有初态读取与零运动导入核验。"""
import gzip
import importlib
import json
import os
from pathlib import Path
from qualified_closure_dynamics_v1.protocol import read, save, sha, require
from qualified_closure_dynamics_v3.guarded_imports import zero_motion
from qualified_closure_dynamics_v3.protocol import validate_runtime

ROOT = Path(__file__).resolve().parent
PROJECT, RUN, PREPARED = ROOT.parent, ROOT / 'run', ROOT / 'prepared'
OLD = PROJECT / 'qualified_closure_dynamics_v4/run'
PARAMETERS = PROJECT / 'qualified_closure_reachability_v1/run/parameters.json'
XML = PROJECT / 'qualified_closure_reachability_v1/run/source_snapshot/2f85.xml'
ORIGINAL = PROJECT / 'qualified_task_v1/run/initial_v2/978505/initial_observation/source_state.npz'


def load_all():
    from reflection.__main__ import bootstrap
    bootstrap()
    for name in ('initial', 'model', 'algebra', 'guards', 'register', 'diagnose', 'audit'):
        importlib.import_module('qualified_initial_state_v1.' + name)


def verify():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    manifest = read(PREPARED / 'manifest.json')
    for name, digest in manifest['identities'].items():
        require(sha(name) == digest, 'Frozen source changed: ' + name)
    with zero_motion() as counts:
        load_all()
        with gzip.open(PREPARED / 'runtime.json.gz', 'rt', encoding='utf-8') as stream:
            checked = validate_runtime(json.load(stream))
        require(not any(counts.values()), 'Construction/integration during imports')
    require(read(OLD / 'claim.json')['consumed'] == 1, 'Original claim changed')
    return dict(verified_identities=len(manifest['identities']), import_counts=counts, **checked)


def input_states():
    import numpy as np
    with np.load(OLD / 'initial_transform.npz', allow_pickle=False) as data:
        states = {name: data[name].copy() for name in ('before', 'after')}
    with np.load(ORIGINAL, allow_pickle=False) as data:
        np.testing.assert_array_equal(data['state'], states['before'])
    require(all(np.isfinite(value).all() for value in states.values()), 'Nonfinite saved state')
    return states


def recorded_equalities():
    text = (OLD / 'initial.json').read_text(encoding='utf-8')
    offset = text.index('"equalities":') + len('"equalities":')
    return json.JSONDecoder().raw_decode(text[offset:].lstrip())[0]
