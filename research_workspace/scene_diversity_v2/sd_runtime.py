"""进程内注入，退出后恢复标签、场景和相机方法。"""
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from reflection import language
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from diversity import scene
from sd_scene import apply
from sd_appearance import labels


def camera_reset(original):
    def reset(env):
        result = original(env)
        cid = env.mj_model.camera('cam').id
        env.camera_name = 'cam'
        env.camera_id = cid
        env.fovy = np.deg2rad(float(env.mj_model.cam_fovy[cid]))
        return result
    return reset


def render(env):
    env.mj_renderer.update_scene(env.mj_data, 'cam')
    env.mj_depth_renderer.update_scene(env.mj_data, 'cam')
    return dict(img=env.mj_renderer.render(), depth=env.mj_depth_renderer.render())


@contextmanager
def context(config):
    with ExitStack() as stack:
        stack.enter_context(patch.object(scene, 'apply_scene', lambda spec, _: apply(spec, config)))
        stack.enter_context(patch.object(UR5GraspEnv, 'reset', camera_reset(UR5GraspEnv.reset)))
        stack.enter_context(patch.object(UR5GraspEnv, 'render', render))
        if config['appearance']:
            mapping = labels(config['appearance'])
            aliases = {name: (mapping[name], name) for name in config['appearance']}
            stack.enter_context(patch.dict(language.LABELS, mapping))
            stack.enter_context(patch.dict(language.DESTINATION_ALIASES, aliases, clear=True))
        yield
