"""从环境创建之前阻断所有积分、规划和闭合入口。"""
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
import mujoco
from scipy import optimize
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv


def blocked(counts, label):
    def call(*args, **kwargs):
        counts[label] += 1
        raise RuntimeError('Zero-integration scene check forbids '+label)
    return call


@contextmanager
def no_motion():
    counts = dict(integration=0, environment_step=0, close=0, planning=0, optimizer=0,
                  reset=0, spec_compile=0, binary_load=0)
    def counted(original, label):
        def call(*args, **kwargs):
            counts[label] += 1
            return original(*args, **kwargs)
        return call
    with ExitStack() as stack:
        for name in ('mj_step', 'mj_step1', 'mj_step2'):
            stack.enter_context(patch.object(mujoco, name, blocked(counts, 'integration')))
        stack.enter_context(patch.object(UR5GraspEnv, 'step', blocked(counts, 'environment_step')))
        stack.enter_context(patch.object(grasp.GraspFlow, 'close_gripper', blocked(counts, 'close')))
        stack.enter_context(patch.object(grasp, '_run_planners', blocked(counts, 'planning')))
        for name in ('minimize', 'least_squares'):
            stack.enter_context(patch.object(optimize, name, blocked(counts, 'optimizer')))
        for owner, name, label in ((UR5GraspEnv, 'reset', 'reset'),
                                   (mujoco.MjSpec, 'compile', 'spec_compile'),
                                   (mujoco.MjModel, 'from_binary_path', 'binary_load')):
            stack.enter_context(patch.object(owner, name, counted(getattr(owner, name), label)))
        yield counts


def require_no_motion(counts):
    assert all(counts[k] == 0 for k in ('integration', 'environment_step', 'close', 'planning', 'optimizer'))
