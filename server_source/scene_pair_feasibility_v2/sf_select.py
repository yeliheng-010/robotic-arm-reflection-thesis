"""只依据真实渲染的可见性选相机，不读取搬运成败。"""
from copy import deepcopy
import mujoco
import numpy as np
from sd_runtime import context
from sd_scene import apply
from sd_inventory import root_boxes
from sd_config import MOVING
from sd_render import visibility, capture, depth_check
from sd_common import save
from reflection.sim_sensing import SegmentationRenderer
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from grasp_process import camera_calibration_from_env
from sf_camera import PROPOSAL_BUDGET, project, framed, proposal
from sf_gate import accepted

TASK_BODIES = ('RedBlock', 'BlueBin', 'PurpleCapsule', 'RedBin')
SETTLE_STEPS = 500


def set_camera(env, camera):
    cid = env.mj_model.camera('cam').id
    quat = np.empty(4)
    mujoco.mju_mat2Quat(quat, np.asarray(camera['rotation']).ravel())
    env.mj_model.cam_pos[cid] = camera['position']
    env.mj_model.cam_quat[cid] = quat
    env.mj_model.cam_fovy[cid] = camera['fovy']
    env.fovy = np.deg2rad(camera['fovy'])
    mujoco.mj_forward(env.mj_model, env.mj_data)


def verify_projection(env, camera, boxes):
    points = np.array([(np.array(b[0])+b[1])/2 for b in boxes.values()])
    pixels, _ = project(points, camera)
    transform, intrinsics = camera_calibration_from_env(env)
    local = (points-transform.t)@transform.R
    fx, fy, cx, cy = intrinsics
    actual = local[:, :2]/local[:, 2:3]*[fx, fy]+[cx, cy]
    np.testing.assert_allclose(actual, pixels, atol=1e-6, rtol=0)


def search(env, renderer, config):
    boxes = {name: box for name, box in root_boxes(env.mj_model, env.mj_data).items() if name in MOVING}
    attempts = []
    for index in range(PROPOSAL_BUDGET):
        camera = config['camera'] if index == 0 else proposal(config['seed'], index, boxes=boxes)
        framing = framed(boxes, camera)
        row = dict(index=index, camera=camera, framing=framing, visibility=None,
                   calibration=None, accepted=False)
        if framing['passed']:
            set_camera(env, camera)
            verify_projection(env, camera, boxes)
            roots = renderer.root_map(env.mj_data)
            row['visibility'] = visibility(env, roots, renderer)
            if all(row['visibility'][name]['qualified'] for name in TASK_BODIES):
                row['calibration'] = depth_check(env, env.render()['depth'], roots)
                row['accepted'] = accepted(framing, row['visibility'], row['calibration'])
        attempts.append(row)
        if row['accepted']:
            return camera, attempts
    return None, attempts


def select(config, folder):
    folder.mkdir(parents=True, exist_ok=False)
    with context(config):
        env = UR5GraspEnv(headless=True, model_editor=lambda spec: apply(spec, config))
        renderer = None
        try:
            env.reset()
            for _ in range(SETTLE_STEPS):
                env.step()
            renderer = SegmentationRenderer(env.mj_model, env.height, env.width)
            camera, attempts = search(env, renderer, config)
            result = dict(seed=config['seed'], accepted=camera is not None, attempts=attempts)
            result['settled_boxes'] = {name: box for name, box in root_boxes(env.mj_model, env.mj_data).items()
                                       if name in MOVING}
            if camera is not None:
                result['capture'] = capture(env, folder)
                assert result['capture']['calibration']['passed']
        finally:
            if renderer is not None:
                renderer.close()
            env.close()
    save(folder/'selection.json', result)
    updated = deepcopy(config)
    if camera is not None:
        updated['camera'] = camera
    updated['camera_accepted'] = camera is not None
    return updated, result
