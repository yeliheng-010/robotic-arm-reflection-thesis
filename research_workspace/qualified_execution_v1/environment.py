"""每个作业独立创建环境；从已资格初态恢复后不隐藏重置。"""
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
import numpy as np
import mujoco
from reflection.__main__ import bootstrap
bootstrap()
from cv_select import scene
from audit_motion_live import UR5e, set_robot_config, guard_context
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from qualified_task_v1.snapshot import forbid
from qualified_execution_v1.common import PROJECT, SEED


def state(env):
    spec = mujoco.mjtState.mjSTATE_INTEGRATION
    values = np.empty(mujoco.mj_stateSize(env.mj_model, spec))
    mujoco.mj_getState(env.mj_model, env.mj_data, values, spec)
    return values


@contextmanager
def opened(case, guard, *, static):
    with scene(case['config']) as (env, _), ExitStack() as stack:
        source = PROJECT/f'qualified_task_v1/run/initial_v2/{SEED}/initial_observation/source_state.npz'
        with np.load(source) as data:
            mujoco.mj_setState(env.mj_model, env.mj_data, data['state'], mujoco.mjtState.mjSTATE_INTEGRATION)
            mujoco.mj_forward(env.mj_model, env.mj_data)
            np.testing.assert_array_equal(data['state'], state(env))
        stack.enter_context(patch.object(UR5e, 'set_robot_config', set_robot_config))
        stack.enter_context(guard_context(case['item'], guard))
        stack.enter_context(self_context())
        stack.enter_context(joint_context(case['config']))
        if static:
            for name in ('mj_step', 'mj_step1', 'mj_step2'):
                stack.enter_context(patch.object(mujoco, name, forbid))
        yield env
