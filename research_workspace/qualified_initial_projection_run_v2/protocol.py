"""独立几何授权与独占claim，不授予动力学预算。"""
import os
from pathlib import Path
from qualified_closure_dynamics_v1.protocol import read, save, sha, require
from qualified_initial_projection_v2.preflight import verify as verify_parent

ROOT = Path(__file__).resolve().parent
PROJECT, RUN = ROOT.parent, ROOT / 'run'
BUDGET = dict(sides=2, attempts_per_side=1, audits=1, initialization_steps=0,
              integration_steps=0, model_generations=0, training_runs=0)
RULES_SHA = '9a8f6be6541378d7c6cec1a5e09505f9d2f50d0be2f21f90486791355afab07e'


def verify():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    for name, digest in read(ROOT / 'BINDINGS.json').items():
        require(sha(PROJECT / name) == digest, 'Frozen entrypoint changed: '+name)
    require(sha(ROOT / 'RULES.json') == RULES_SHA, 'Rules changed')
    identities = verify_parent()
    rules = read(ROOT / 'RULES.json')
    base = PROJECT / 'qualified_initial_projection_v2'
    require(sha(base / 'BINDINGS.json') == rules['algorithm_bindings_sha256'], 'Algorithm changed')
    require(sha(base / 'prepared/result.json') == rules['preflight_result_sha256'], 'Preflight changed')
    require(read(base / 'prepared/result.json')['passed'], 'Preflight failed')
    state = PROJECT / 'qualified_closure_dynamics_v4/run/initial_transform.npz'
    require(sha(state) == rules['source_state_sha256'], 'Reference state changed')
    return identities


def validate_authorization(auth):
    require(auth.get('kind') == 'isolated_geometry_only', 'Wrong authorization scope')
    require(auth.get('geometry_execution_authorized') is True, 'Geometry not authorized')
    require(auth.get('dynamics_execution_authorized') is False, 'Dynamics must remain disabled')
    require(auth.get('budget') == BUDGET, 'Wrong budget')
    require(all(type(x) is int for x in auth['budget'].values()), 'Budget must use integers')
    require(auth.get('rules_sha256') == RULES_SHA, 'Wrong rules')


def claim(auth, folder, *, name):
    validate_authorization(auth)
    require(name in ('construction', 'right', 'left', 'audit'), 'Unknown claim')
    if name != 'construction':
        require(read(Path(folder) / 'construction_claim.json')['consumed'] == 1,
                'Construction claim missing')
    save(Path(folder) / (name+'_claim.json'), dict(consumed=1, name=name,
        job=os.environ.get('SLURM_JOB_ID', 'test'), rules_sha256=RULES_SHA, integration_budget=0))


def authorization():
    auth = read(ROOT / 'authorization.json')
    validate_authorization(auth)
    require(auth['bindings_sha256'] == sha(ROOT / 'BINDINGS.json'), 'Authorization binding changed')
    require(auth['prepared_sha256'] == sha(ROOT / 'prepared.json'), 'Preparation evidence changed')
    require(read(ROOT / 'prepared.json')['passed'], 'Preparation failed')
    return auth
