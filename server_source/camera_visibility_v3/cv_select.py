"""在原相机范围内确定性选择；失败保留原始原因，禁止回退。"""
from copy import deepcopy
from contextlib import contextmanager
import cv2
import mujoco
import numpy as np
from sd_runtime import context
from sd_scene import apply
from sd_inventory import root_boxes
from sd_render import depth_check
from sd_common import read, save, sha
from sf_camera import framed, proposal
from sf_select import set_camera, verify_projection
from reflection.sim_sensing import SegmentationRenderer
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from cv_metrics import measure
from cv_policy import REQUIRED, require_frame

SETTLE_STEPS = 500
PROPOSAL_BUDGET = 256


@contextmanager
def scene(config):
    with context(config):
        env = UR5GraspEnv(headless=True, model_editor=lambda spec: apply(spec, config))
        renderer = None
        try:
            env.reset()
            for _ in range(SETTLE_STEPS):
                env.step()
            mujoco.mj_forward(env.mj_model, env.mj_data)
            renderer = SegmentationRenderer(env.mj_model, env.height, env.width)
            yield env, renderer
        finally:
            if renderer is not None:
                renderer.close()
            env.close()


def evaluate(env, renderer, camera, *, boxes):
    set_camera(env, camera)
    verify_projection(env, camera, boxes)
    framing = framed(boxes, camera)
    report, roots = measure(env, renderer, framing)
    report.update(framing=framing, calibration=None, accepted=False)
    if report['gate']['passed']:
        report['calibration'] = depth_check(env, env.render()['depth'], roots)
        report['accepted'] = bool(report['calibration']['passed'])
    return report


def image(env, path):
    rgb = env.render()['img']
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)):
        raise RuntimeError('Unable to save actual RGB')
    return sha(path)


def search(env, renderer, config, *, folder, boxes, cached):
    attempts = deepcopy(cached)
    for index in range(len(cached), PROPOSAL_BUDGET):
        camera = config['camera'] if index == 0 else proposal(config['seed'], index, boxes=boxes)
        if index and not framed(boxes, camera)['passed']:
            row = dict(index=index, camera=camera, accepted=False, status='framing_rejected')
        else:
            row = evaluate(env, renderer, camera, boxes=boxes)
            row.update(index=index, camera=camera)
        attempts.append(row)
        if index == 0:
            row['rgb_sha256'] = image(env, folder/'before.png')
        if row['accepted']:
            require_frame(row['gate'])
            row['rgb_sha256'] = image(env, folder/'after.png')
            return camera, attempts
    return None, attempts


def select(config, folder, *, prior=None):
    """新采集需先调用该入口，只消费返回的合格配置。"""
    folder.mkdir(parents=True, exist_ok=False)
    if config['group'] != 'varied_noisy':
        raise ValueError('Keep baseline configuration unchanged')
    with scene(config) as (env, renderer):
        all_boxes = root_boxes(env.mj_model, env.mj_data)
        boxes = {name: all_boxes[name] for name in REQUIRED}
        before = env.mj_data.qpos.copy()
        cached = []
        if prior is not None:
            cached = read(prior/'selection.json')['attempts']
            assert all(not row['accepted'] for row in cached)
            assert [row['index'] for row in cached] == list(range(len(cached)))
            assert cached[0]['camera'] == config['camera']
            assert image(env, folder/'before.png') == sha(prior/'before.png')
        camera, attempts = search(env, renderer, config, folder=folder, boxes=boxes, cached=cached)
        assert np.array_equal(before, env.mj_data.qpos), 'Camera selection moved the scene'
        updated = deepcopy(config) if camera else None
        if updated is not None:
            updated['camera'] = camera
            save(folder/'accepted_config.json', updated)
        result = dict(seed=config['seed'], accepted=updated is not None, attempts=attempts,
                      unchanged_qpos=True, required=list(REQUIRED), semantics_verified=False)
        save(folder/'selection.json', result)
    return updated, result


def check_observation(env, renderer, camera):
    """可用于每次实际观测；初态通过不豁免运动后的重新检查。"""
    boxes = root_boxes(env.mj_model, env.mj_data)
    report = evaluate(env, renderer, camera, boxes={name: boxes[name] for name in REQUIRED})
    require_frame(report['gate'])
    if not report['accepted']:
        raise ValueError('Observation calibration failed')
    return report
