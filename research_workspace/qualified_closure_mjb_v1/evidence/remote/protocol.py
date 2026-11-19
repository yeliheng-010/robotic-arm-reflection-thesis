"""独立零初始化协议；只有已绑定准备的显式授权可消费轨迹。"""
import os
from pathlib import Path
from qualified_closure_dynamics_v1.protocol import read, save, sha, require, commands

ROOT = Path(__file__).resolve().parent
PROJECT, RUN, PREPARED, VERIFIED = ROOT.parent, ROOT/'run', ROOT/'prepared', ROOT/'verification'
PLAN = PROJECT/'qualified_closure_mjb_plan_v1'
DIAGNOSTIC_ID = 'qualified_closure_mjb_v1-978505'
BUDGET = dict(trajectories=1, setup_steps=0, task_steps=1000, model_calls=0,
              full_task_attempts=0, training_runs=0, zero_integration_audits=1,
              job_wall_seconds=600, loop_wall_seconds=120)


def proposal():
    return read(PLAN/'protocol.proposed.json')


def check_identities(identities):
    require(bool(identities), 'Empty identities')
    for path, digest in identities.items():
        require(sha(path) == digest, 'Changed frozen source: '+str(path))


def validate_authorization(auth, *, expected, preparation_digest):
    require(auth.get('execution_authorized') is True, 'Dynamics not authorized')
    require(auth.get('diagnostic_id') == DIAGNOSTIC_ID, 'Wrong diagnostic ID')
    require(auth.get('budget') == BUDGET, 'Wrong budget')
    require(all(type(x) is int for x in auth['budget'].values()), 'Integer budgets required')
    require(bool(auth.get('approval_reference')), 'Missing approval reference')
    require(auth.get('identities') == expected and bool(expected), 'Wrong identity set')
    require(auth.get('preparation_sha256') == preparation_digest, 'Preparation changed')


def consume(auth, folder, *, expected, preparation_digest):
    validate_authorization(auth, expected=expected, preparation_digest=preparation_digest)
    save(folder/'claim.json', dict(consumed=1, diagnostic_id=DIAGNOSTIC_ID,
         job=os.environ.get('SLURM_JOB_ID'), preparation_sha256=preparation_digest))


def verify_sources():
    from qualified_closure_mjb_plan_v1.validate import sources
    identities, _ = sources()
    require(read(PLAN/'preparation/result.json')['plan_validated'], 'Unverified plan')
    for name, digest in read(ROOT/'BINDINGS.json').items():
        require(sha(PROJECT/name) == digest, 'Changed new source: '+name)
        identities[str(PROJECT/name)] = digest
    identities[str(ROOT/'BINDINGS.json')] = sha(ROOT/'BINDINGS.json')
    return identities


def inventory(folder):
    return {p.name: sha(p) for p in folder.iterdir() if p.is_file()}
