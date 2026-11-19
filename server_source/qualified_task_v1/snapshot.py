"""快照私有模型与数据；绝不对运行环境调用forward或渲染。"""
from contextlib import contextmanager, ExitStack
from copy import copy
from types import SimpleNamespace
from unittest.mock import patch
import mujoco
import numpy as np
from qualified_task_v1.integrity import fingerprint, unchanged


def clone(env):
    model = copy(env.mj_model)
    data = mujoco.MjData(model)
    spec = mujoco.mjtState.mjSTATE_INTEGRATION
    state = np.empty(mujoco.mj_stateSize(env.mj_model, spec))
    mujoco.mj_getState(env.mj_model, env.mj_data, state, spec)
    mujoco.mj_setState(model, data, state, spec)
    assert model is not env.mj_model and data is not env.mj_data
    for name in ('qpos', 'qvel', 'ctrl', 'xpos', 'geom_xpos', 'cam_xpos'):
        assert not np.shares_memory(getattr(data, name), getattr(env.mj_data, name))
    for name in ('cam_pos', 'cam_quat', 'cam_fovy', 'geom_group'):
        assert not np.shares_memory(getattr(model, name), getattr(env.mj_model, name))
    mujoco.mj_forward(model, data)
    return SimpleNamespace(mj_model=model, mj_data=data, width=env.width,
        height=env.height, fovy=env.fovy, camera_name='cam', camera_id=model.camera('cam').id)


def forbid(*args, **kwargs):
    raise RuntimeError('Integration is forbidden during snapshot observation')


@contextmanager
def isolated(env, audit):
    before = fingerprint(env)
    original = mujoco.mj_forward
    def forward(model, data):
        if model is env.mj_model or data is env.mj_data:
            raise RuntimeError('Live forward is forbidden during observation')
        return original(model, data)
    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(mujoco, 'mj_forward', forward))
            for name in ('mj_step', 'mj_step1', 'mj_step2'):
                stack.enter_context(patch.object(mujoco, name, forbid))
            yield clone(env)
    finally:
        audit.update(unchanged(before, fingerprint(env)))


@contextmanager
def rendered(snapshot):
    from reflection.sim_sensing import SegmentationRenderer
    from sensor_independent_v1.sensor import paired
    with ExitStack() as stack:
        for name in ('mj_renderer', 'mj_depth_renderer'):
            renderer = mujoco.Renderer(snapshot.mj_model, snapshot.height, snapshot.width)
            stack.callback(renderer.close)
            setattr(snapshot, name, renderer)
        snapshot.mj_depth_renderer.enable_depth_rendering()
        segment = SegmentationRenderer(snapshot.mj_model, snapshot.height, snapshot.width)
        stack.callback(segment.close)
        resources, samples = stack.enter_context(paired(snapshot, segment))
        yield resources, samples
