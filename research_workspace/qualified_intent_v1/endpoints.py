"""模型抓姿仅做原IK/几何端点检查；不生成真值放置目标。"""
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch
import mujoco
import numpy as np
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
from cv_select import scene
from goal_endpoints import inspect, CONFIGS
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from audit_motion_live import UR5e, set_robot_config, guard_context
from qualified_task_v1.snapshot import forbid
from qualified_task_v1.integrity import fingerprint, unchanged
from model_grasp_intent_v1.geometry import propose
from model_grasp_intent_v1.model import parse
from qualified_intent_v1.common import ROOT, PROJECT, RUN as INPUT, read, save, sha
from qualified_intent_v1.model_v2 import OUTPUT as RUN, verified as verify


def check(case, proposal, *, seed):
    with scene(case['config']) as (env, _), ExitStack() as stack:
        path = PROJECT/f'qualified_task_v1/run/initial_v2/{seed}/initial_observation/source_state.npz'
        with np.load(path) as snapshot:
            mujoco.mj_setState(env.mj_model, env.mj_data, snapshot['state'], mujoco.mjtState.mjSTATE_INTEGRATION)
        mujoco.mj_forward(env.mj_model, env.mj_data)
        for name in ('mj_step', 'mj_step1', 'mj_step2'):
            stack.enter_context(patch.object(mujoco, name, forbid))
        stack.enter_context(patch.object(UR5e, 'set_robot_config', set_robot_config))
        stack.enter_context(guard_context(case['item'], {}))
        stack.enter_context(self_context())
        stack.enter_context(joint_context(case['config']))
        pose = sm.SE3(np.array(proposal['pose']))
        flow = SimpleNamespace(env=env, robot=env.robot, q0=env.robot.get_joint(),
                               q1=env.robot.get_joint(), T_wo=pose)
        before = fingerprint(env)
        rows = [dict(config=list(c), **inspect(flow, pose, config=c, item=case['item'])) for c in CONFIGS]
        isolation = unchanged(before, fingerprint(env))
    return dict(rows=rows, passing=sum(r['ok'] for r in rows), state_check=isolation,
                full_path_verified=False, physical_attempts=0)


def evaluate(entry, cases):
    seed, folder = entry['seed'], RUN/str(entry['seed'])
    response = read(folder/'response.json')
    validated = read(folder/'validated.json')
    if not validated['valid']:
        return dict(seed=seed, status='invalid_model_output', physical_attempts=0)
    action = parse(response)['action']
    assert action == validated['action']
    if action['id'] == 'STOP':
        return dict(seed=seed, status='model_stopped', physical_attempts=0)
    observation = read(INPUT/str(seed)/'observation.json')
    proposal = propose(observation['target_points'], observation['nominal'], action)
    save(folder/'proposal.json', proposal)
    if proposal['status'] != 'proposal':
        return dict(seed=seed, status='proposal_rejected', reason=proposal['reason'], physical_attempts=0)
    result = check(cases[str(seed)], proposal, seed=seed)
    save(folder/'private_endpoints.json', result)
    return dict(seed=seed, status='grasp_endpoint_checked', passing=result['passing'],
                full_path_verified=False, physical_attempts=0)


def main():
    manifest = verify()
    cases = read(PROJECT/'qualified_task_v1/run/manifest.json')['cases']
    paths = [ROOT/'endpoints.py', ROOT/'endpoints.sbatch']
    paths.extend(p for p in RUN.rglob('*') if p.is_file())
    save(RUN/'endpoint_manifest.json', dict(identities={str(p): sha(p) for p in paths},
        purpose='Safety evaluation only; no oracle targets to model or controller'))
    rows = [evaluate(entry, cases) for entry in manifest['entries']]
    verify()
    assert all(sha(p) == h for p, h in read(RUN/'endpoint_manifest.json')['identities'].items())
    save(RUN/'endpoint_result.json', dict(rows=rows, physical_attempts=0, training_runs=0,
                                        model_calls=2, full_task_success=None))
    print(rows, flush=True)


if __name__ == '__main__':
    main()
