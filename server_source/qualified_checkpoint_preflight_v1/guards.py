"""区分场景初始化步进与恢复后的静态预检；记录禁止调用。"""
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
import mujoco
import grasp_process as grasp
from qualified_path_v1 import worker as paths
from qualified_execution_v1 import environment

STEP_NAMES = ('mj_step', 'mj_step1', 'mj_step2')


def counted(function, counts, *, name):
    def call(*args, **kwargs):
        counts[name] += 1
        return function(*args, **kwargs)
    return call


@contextmanager
def static_scope():
    counts = dict(setup_calls={name: 0 for name in STEP_NAMES}, environments=0,
                  blocked_task_integration_requests=0, blocked_gripper_close_requests=0)
    original_scene = paths.scene
    assert environment.scene is original_scene
    @contextmanager
    def scene(config):
        with ExitStack() as lifetime:
            with ExitStack() as setup:
                for name in STEP_NAMES:
                    setup.enter_context(patch.object(mujoco, name,
                        counted(getattr(mujoco, name), counts['setup_calls'], name=name)))
                pair = lifetime.enter_context(original_scene(config))
            counts['environments'] += 1
            yield pair
    def forbid_step(*args, **kwargs):
        counts['blocked_task_integration_requests'] += 1
        raise RuntimeError('Task integration forbidden in fixed-action preflight')
    def forbid_close(*args, **kwargs):
        counts['blocked_gripper_close_requests'] += 1
        raise RuntimeError('Physical gripper closure forbidden in preflight')
    with ExitStack() as stack:
        for module in (paths, environment):
            stack.enter_context(patch.object(module, 'scene', scene))
            stack.enter_context(patch.object(module, 'forbid', forbid_step))
        stack.enter_context(patch.object(grasp.GraspFlow, 'close_gripper', forbid_close))
        yield counts
