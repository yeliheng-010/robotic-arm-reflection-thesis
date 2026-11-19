"""诊断来源与禁止优化/积分保护。"""
import json
import os
import sys
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch
from qualified_closure_dynamics_v1.protocol import read, save, sha, require
from qualified_closure_dynamics_v3.guarded_imports import zero_motion, blocker

ROOT = Path(__file__).resolve().parent
PROJECT, RUN = ROOT.parent, ROOT / 'run'
PARENT = PROJECT / 'qualified_initial_projection_v1'
STATE = PROJECT / 'qualified_closure_dynamics_v4/run/initial_transform.npz'
PARAMETERS = PROJECT / 'qualified_closure_reachability_v1/run/parameters.json'
XML = PROJECT / 'qualified_closure_reachability_v1/run/source_snapshot/2f85.xml'


def verify():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    bindings = read(ROOT / 'BINDINGS.json')
    for name, digest in bindings.items():
        require(sha(PROJECT / name) == digest, 'Diagnostic binding changed: ' + name)
    identities = read(PARENT / 'prepared/manifest.json')['identities']
    for name, digest in identities.items():
        require(sha(name) == digest, 'Parent source changed: ' + name)
    for name, digest in read(PARENT / 'run/inventory.json').items():
        require(sha(PARENT / 'run' / name) == digest, 'Parent evidence changed: ' + name)
    require(not (PARENT / 'run/candidate_state.npz').exists(), 'Unexpected candidate')
    require(not (PARENT / 'authorization.json').exists(), 'Unexpected dynamics authorization')
    return identities


def loaded_sources(identities):
    files = {}
    for name, module in list(sys.modules.items()):
        if name.split('.')[0] not in ('numpy', 'scipy', 'mujoco'):
            continue
        path = getattr(module, '__file__', None)
        if path and Path(path).is_file():
            require(path in identities, 'Unbound numerical source: ' + path)
            files[path] = sha(path)
            require(files[path] == identities[path], 'Numerical source changed: ' + path)
    return files


@contextmanager
def diagnostic_only():
    import scipy.optimize as optimize
    import scipy.optimize._slsqp_py as wrapper
    import scipy.optimize._slsqp as native
    counts = dict(optimizer=0)
    with zero_motion() as motion, ExitStack() as stack:
        for module, name in ((optimize, 'minimize'), (optimize, 'fmin_slsqp'),
                             (wrapper, '_minimize_slsqp'), (wrapper, 'slsqp'), (native, 'slsqp')):
            stack.enter_context(patch.object(module, name, blocker(counts, 'optimizer')))
        yield counts, motion


def source_snapshot(identities):
    import scipy
    import scipy.optimize._slsqp_py as wrapper
    import scipy.optimize._numdiff as difference
    paths = [Path(wrapper.__file__), Path(difference.__file__)]
    saved = []
    for path in paths:
        require(sha(path) == identities[str(path)], 'SciPy source mismatch')
        target = RUN / path.name
        with target.open('xb') as stream:
            stream.write(path.read_bytes())
        saved.append(dict(path=str(path), sha256=sha(path)))
    return dict(scipy_version=scipy.__version__, files=saved,
                original_iteration_trace_available=False, internal_hessian_available=False)
