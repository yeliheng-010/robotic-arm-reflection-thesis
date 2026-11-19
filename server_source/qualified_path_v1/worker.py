from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import mujoco
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
from cv_select import scene
from audit_motion_live import UR5e, set_robot_config, guard_context
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from qualified_task_v1.snapshot import forbid
from qualified_task_v1.integrity import fingerprint, unchanged
from qualified_path_v1 import planning
from qualified_path_v1.common import ROOT, PROJECT, RUN, SEEDS, read, save, sha, verify


def approved(seed):
    if seed == 978501:
        folder = PROJECT/f'qualified_intent_v1/run_v3/{seed}'
    else:
        feedback = PROJECT/'qualified_feedback_v1/run'
        selected = next((r for r in read(feedback/'result.json')['rows'] if r['status'] == 'ready'), None)
        if selected is None:
            return None
        folder = feedback/f"decision_{selected['ordinal']}"
    assert read(folder/'private_endpoints.json')['passing'] > 0
    return folder


def inspect(case, proposal, *, geometry):
    seed = case['item']['seed']
    with scene(case['config']) as (env, _), ExitStack() as stack:
        with np.load(PROJECT/f'qualified_task_v1/run/initial_v2/{seed}/initial_observation/source_state.npz') as state:
            mujoco.mj_setState(env.mj_model, env.mj_data, state['state'], mujoco.mjtState.mjSTATE_INTEGRATION)
        mujoco.mj_forward(env.mj_model, env.mj_data)
        for name in ('mj_step', 'mj_step1', 'mj_step2'):
            stack.enter_context(patch.object(mujoco, name, forbid))
        stack.enter_context(patch.object(UR5e, 'set_robot_config', set_robot_config))
        stack.enter_context(guard_context(case['item'], {}))
        stack.enter_context(self_context())
        stack.enter_context(joint_context(case['config']))
        flow = SimpleNamespace(env=env, robot=env.robot, q0=env.robot.get_joint().copy(),
            q1=env.robot.get_joint().copy(), T_wo=sm.SE3(np.asarray(proposal['pose'])))
        before, joints = fingerprint(env), env.robot.get_joint().copy()
        result = planning.run(flow, case, geometry=geometry, proposal=proposal)
        np.testing.assert_array_equal(joints, env.robot.get_joint())
        result['state_check'] = unchanged(before, fingerprint(env))
    return result


def registration():
    previous = verify()
    paths = [ROOT/n for n in ('planning.py', 'worker.py', 'plan.sbatch')]
    paths += [p for p in (RUN/'goals').rglob('*') if p.is_file()]
    paths += [PROJECT/'qualified_feedback_v1/run/result.json']
    for seed in SEEDS:
        folder = approved(seed)
        if folder is not None:
            paths += [folder/'proposal.json', folder/'private_endpoints.json']
    save(RUN/'planning_manifest.json', dict(identities={str(p): sha(p) for p in paths},
        parent_sha256=sha(RUN/'manifest.json'), max_planning_sessions=2,
        time_limit_per_layout_s=240, max_task_attempts=0, max_model_calls=0, max_training_runs=0))
    return previous


def main():
    registration()
    cases = read(PROJECT/'qualified_task_v1/run/manifest.json')['cases']
    rows = []
    for seed in SEEDS:
        folder = approved(seed)
        goal = RUN/f'goals/{seed}'
        if folder is None or not read(goal/'result.json')['accepted']:
            rows.append(dict(seed=seed, status='precondition_rejected', passed=False))
            continue
        result = inspect(cases[str(seed)], read(folder/'proposal.json'), geometry=read(goal/'geometry.json'))
        save(RUN/f'planning/{seed}/private_result.json', result)
        rows.append(dict(seed=seed, status=result['plan']['status'], passed=result['strict']['passed']))
    verify()
    assert all(sha(p) == h for p, h in read(RUN/'planning_manifest.json')['identities'].items())
    save(RUN/'planning_result.json', dict(rows=rows, physical_attempts=0, model_calls=0, training_runs=0))
    print(rows, flush=True)


if __name__ == '__main__':
    main()
