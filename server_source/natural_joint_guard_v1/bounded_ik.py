"""按真实编译关节/控制范围选择等价IK角度，并拒绝跨限位跳变。"""
import math
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
import numpy as np
from manipulator_grasp.arm.robot import UR5e
from sd_scene import compiled
import cm_geometry
import route_geometry
import goal_endpoints

PERIOD = 2*math.pi
JUMP_LIMIT_RAD = math.pi
EPS = 1e-9


def representatives(q, reference, bounds):
    if len(q)!=6:
        return np.array([])
    answer = []
    for value, prior, (low, high) in zip(q, reference, bounds):
        if not all(math.isfinite(float(v)) for v in (value,prior,low,high)):
            return np.array([])
        lower = math.ceil((low-value)/PERIOD)
        upper = math.floor((high-value)/PERIOD)
        if lower > upper:
            return np.array([])
        options = [float(value+k*PERIOD) for k in range(lower, upper+1)]
        answer.append(min(options, key=lambda v: abs(v-prior)))
    return np.array(answer)


def limits(model):
    bounds = []
    for index in range(6):
        jid = int(model.actuator_trnid[index,0])
        assert model.jnt_limited[jid] and model.actuator_ctrllimited[index]
        low = max(model.jnt_range[jid,0], model.actuator_ctrlrange[index,0])
        high = min(model.jnt_range[jid,1], model.actuator_ctrlrange[index,1])
        assert low < high
        bounds.append([float(low), float(high)])
    return np.array(bounds)


def inverse_wrapper(original, bounds):
    def inverse(robot, *args, **kwargs):
        reference = robot.get_joint().copy()
        raw = original(robot, *args, **kwargs)
        selected = representatives(raw, reference, bounds)
        if len(selected)==6:
            np.testing.assert_allclose(robot.fkine(raw).A, robot.fkine(selected).A, atol=1e-8, rtol=0)
        return selected
    return inverse


def sample_wrapper(original, bounds):
    def sample(robot, env, data, *, value, ignore):
        before = robot.get_joint().copy()
        result = original(robot, env, data, value=value, ignore=ignore)
        if not result['ok']:
            return result
        q = np.array([data.joint(name).qpos[0] for name in env.joint_names])
        if np.any(q < bounds[:,0]-EPS) or np.any(q > bounds[:,1]+EPS):
            return dict(ok=False, reason='joint_or_control_limit', q=q.tolist())
        if np.max(np.abs(q-before)) > JUMP_LIMIT_RAD:
            return dict(ok=False, reason='discontinuous_joint_branch', delta=(q-before).tolist())
        return result
    return sample


@contextmanager
def context(config):
    model, _ = compiled(config)
    bounds = limits(model)
    with ExitStack() as stack:
        stack.enter_context(patch.object(UR5e, 'ikine', inverse_wrapper(UR5e.ikine, bounds)))
        for module in (cm_geometry, route_geometry, goal_endpoints):
            stack.enter_context(patch.object(module, 'sample', sample_wrapper(module.sample, bounds)))
        yield bounds
