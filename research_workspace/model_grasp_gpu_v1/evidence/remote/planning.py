"""真实冻结场景的静态规划；禁止仿真步进，结果保留在私有账本。"""
from contextlib import contextmanager
import signal
from unittest.mock import patch
import mujoco
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
import goal_search
from route_audit_v3 import rebuild
from audit_motion_live import UR5e, set_robot_config, guard_context
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from rv_runtime import mode
from jv_context import observation
from jg_geometry import Advisor
from jg_choose import goals_wrapper
from jg_paths import context as paths_context
from routecheck.static import state, unchanged
from model_grasp_intent_v1.bridge import runtime_bridge
from model_grasp_gpu_v1.common import ROOT, SOURCE, read, save


def forbid(*args, **kwargs):
    raise RuntimeError('Motion is forbidden in registered planning replay')


@contextmanager
def deadline(seconds):
    def expired(*args):
        raise TimeoutError('Registered planning deadline')
    old = signal.signal(signal.SIGALRM, expired)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def integration(flow):
    flag = mujoco.mjtState.mjSTATE_INTEGRATION
    values = np.empty(mujoco.mj_stateSize(flow.env.mj_model, flag))
    mujoco.mj_getState(flow.env.mj_model, flow.env.mj_data, values, flag)
    return values


def search(flow, case, events):
    advisor = Advisor(flow, item=case['item'], parameters=case['state']['parameters'], record=events.append)
    with paths_context(), patch.object(goal_search,'option_goals',goals_wrapper(goal_search.option_goals,advisor)):
        return goal_search.choose(flow, item=case['item'], parameters=case['state']['parameters'],
                                  hooks=(grasp.move_to_grasp_pose, grasp.move_to_point))


def inspect(proposal, manifest, folder):
    case, trace, events = manifest['case'], {}, []
    points = np.asarray(read(ROOT/'observation.json')['target_points'])
    with patch.object(UR5e,'set_robot_config',set_robot_config), guard_context(case['item'],{}), \
         self_context(), joint_context(case['config']), mode(case['control']), observation(points,trace), \
         patch.object(goal_search,'LIFTS',(case['state']['parameters']['lift_height'],)), \
         patch.object(mujoco,'mj_step',forbid), patch.object(mujoco,'mj_step1',forbid), \
         patch.object(mujoco,'mj_step2',forbid):
        flow = rebuild(case,read(SOURCE/'actual_plan.json'))
        before, full = state(flow.robot,flow.env), integration(flow)
        bridge = runtime_bridge(points,lambda: search(flow,case,events))
        try:
            with deadline(manifest['planning_timeout_s']):
                result = bridge(proposal)
        finally:
            unchanged(before,state(flow.robot,flow.env))
            np.testing.assert_array_equal(full,integration(flow))
        save(folder/'private_plan.json',bridge.private_result)
        save(folder/'private_trace.json',trace)
        save(folder/'private_events.json',events)
        assert trace['candidate_stages'] and trace['poses'], 'Candidate injection did not run'
    save(folder/'state_check.json',dict(unchanged=True,integration_identical=True,physical_attempts=0))
    return result
