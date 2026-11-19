"""端点不检查相邻步跳变；仅连续路径样本检查跳变，均保留硬限位。"""
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
import numpy as np
from bounded_ik import UR5e, compiled, limits, inverse_wrapper, EPS, JUMP_LIMIT_RAD
import cm_geometry
import route_geometry
import goal_endpoints


def sample_wrapper(original, bounds, *, continuous):
    def sample(robot, env, data, *, value, ignore):
        before = robot.get_joint().copy()
        result = original(robot, env, data, value=value, ignore=ignore)
        if not result['ok']:
            return result
        q = np.array([data.joint(name).qpos[0] for name in env.joint_names])
        if np.any(q < bounds[:,0]-EPS) or np.any(q > bounds[:,1]+EPS):
            return dict(ok=False, reason='joint_or_control_limit', q=q.tolist())
        if continuous and np.max(np.abs(q-before)) > JUMP_LIMIT_RAD:
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
            wrapped = sample_wrapper(module.sample, bounds, continuous=module is route_geometry)
            stack.enter_context(patch.object(module, 'sample', wrapped))
        yield bounds
