"""只编辑本次 MjSpec；旧 XML 和共享模块保持原样。"""
import numpy as np
import mujoco
from cl_design import SCENE
from diversity.scene import yaw_rotate

DIVIDERS = ('safety_divider', 'safety_divider_marker_left', 'safety_divider_marker_right')


def apply(spec, config):
    for name in DIVIDERS:
        geom = spec.geom(name)
        geom.contype, geom.conaffinity = 0, 0
        geom.rgba = [0., 0., 0., 0.]
    for name, values in config.get('bodies', {}).items():
        body = spec.body(name)
        body.pos = values['position']
        yaw_rotate(body, values['yaw_delta'])
    for name, color in config.get('appearance', {}).items():
        for geom in spec.body(name).geoms:
            geom.rgba = color['rgba']
    camera = config.get('camera')
    if camera:
        cam = spec.camera('cam')
        quat = np.empty(4)
        mujoco.mju_mat2Quat(quat, np.array(camera['rotation']).ravel())
        cam.alt.type = mujoco.mjtOrientation.mjORIENTATION_QUAT
        cam.quat, cam.pos, cam.fovy = quat, camera['position'], camera['fovy']


def compiled(config=None):
    spec = mujoco.MjSpec.from_file(str(SCENE))
    apply(spec, config or {})
    model = spec.compile()
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return model, data
