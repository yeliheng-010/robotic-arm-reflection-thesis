"""仅允许指定隔离XML与数据分配，禁止环境、渲染和积分。"""
from contextlib import ExitStack, contextmanager
from unittest.mock import patch
import mujoco


@contextmanager
def kinematics_only(xml):
    from qualified_execution_v1 import environment
    counts = dict(integration=0, scene=0, rendering=0, forbidden_model=0,
                  forward=0, isolated_model=0, data=0)
    def blocked(label):
        def call(*args, **kwargs):
            counts[label] += 1
            raise RuntimeError('Forbidden diagnostic operation: ' + label)
        return call
    original_model, original_data = mujoco.MjModel.from_xml_string, mujoco.MjData
    def compile_model(text):
        if text != xml or counts['isolated_model']:
            return blocked('forbidden_model')()
        counts['isolated_model'] += 1
        return original_model(text)
    def data(model):
        counts['data'] += 1
        return original_data(model)
    with ExitStack() as stack:
        for name in ('mj_step', 'mj_step1', 'mj_step2'):
            stack.enter_context(patch.object(mujoco, name, blocked('integration')))
        stack.enter_context(patch.object(environment, 'scene', blocked('scene')))
        stack.enter_context(patch.object(mujoco, 'Renderer', blocked('rendering')))
        stack.enter_context(patch.object(mujoco, 'mj_forward', blocked('forward')))
        for name in ('from_xml_path', 'from_binary_path'):
            stack.enter_context(patch.object(mujoco.MjModel, name, blocked('forbidden_model')))
        for name in ('from_file', 'from_string', 'compile'):
            stack.enter_context(patch.object(mujoco.MjSpec, name, blocked('forbidden_model')))
        stack.enter_context(patch.object(mujoco.MjModel, 'from_xml_string', compile_model))
        stack.enter_context(patch.object(mujoco, 'MjData', data))
        yield counts
