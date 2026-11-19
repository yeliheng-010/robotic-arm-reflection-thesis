"""场景编译适配器：只编辑本次 MjSpec，不触碰原始 XML。"""
import numpy as np
import mujoco
from diversity.config import SOURCES

GEOMS = dict(zip(SOURCES, ('red_block', 'green_cylinder', 'purple_capsule', 'orange_sphere')))


def yaw_rotate(body, delta):
    if delta == 0:
        return
    quat = np.asarray(body.quat).copy()
    if body.alt.type == mujoco.mjtOrientation.mjORIENTATION_EULER:
        mujoco.mju_euler2Quat(quat, body.alt.euler, 'xyz')
    rotation = np.array([np.cos(delta/2), 0., 0., np.sin(delta/2)])
    output = np.empty(4)
    mujoco.mju_mulQuat(output, rotation, quat)
    body.alt.type = mujoco.mjtOrientation.mjORIENTATION_QUAT
    body.quat = output


def apply_scene(spec, config):
    for name, values in config['bodies'].items():
        body, geom = spec.body(name), spec.geom(GEOMS[name])
        position = np.asarray(body.pos).copy()
        position[:2] = values['xy']
        body.pos = position
        yaw_rotate(body, values['yaw_delta'])
        geom.density *= values['density_scale']
        friction = np.asarray(geom.friction).copy()
        friction[0] *= values['friction_scale']
        geom.friction = friction
    for name, offset in config['containers'].items():
        body = spec.body(name)
        position = np.asarray(body.pos).copy()
        position[:2] += offset
        body.pos = position


class ScenarioFault:
    def __init__(self, original, config):
        self.original, self.config = original, config

    def __getattr__(self, key):
        return getattr(self.original, key)

    def model_editor(self, spec):
        self.original.model_editor(spec)
        apply_scene(spec, self.config)
        if self.name == 'collision':
            height = self.config['faults']['divider_halfheight']
            divider = spec.geom('safety_divider')
            divider.size = [divider.size[0], divider.size[1], height]
            divider.pos = [divider.pos[0], divider.pos[1], height]

    def grasp_bias(self):
        return self.config['faults']['grasp_bias'] if self.name == 'calibration' else self.original.grasp_bias()

    def place_bias(self):
        return self.config['faults']['place_bias'] if self.name == 'placement' else self.original.place_bias()

