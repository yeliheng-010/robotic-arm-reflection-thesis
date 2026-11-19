"""用同相机的隔离轮廓测遮挡，机器人和背景都保留为遮挡物。"""
import cv2
import mujoco
import numpy as np
from cv_policy import REQUIRED, frame_gate


def mask_metrics(mask):
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return dict(pixels=0, short_side=0, long_side=0, largest_component=0)
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    largest = int(stats[1:, cv2.CC_STAT_AREA].max()) if count > 1 else 0
    return dict(pixels=int(len(xs)), short_side=int(min(xs.max()-xs.min()+1,
                ys.max()-ys.min()+1)), long_side=int(max(xs.max()-xs.min()+1,
                ys.max()-ys.min()+1)), largest_component=largest)


def isolated_mask(env, renderer, name):
    model = env.mj_model
    original = model.geom_group.copy()
    members = model.body_rootid[model.geom_bodyid] == model.body(name).id
    options = mujoco.MjvOption()
    options.geomgroup[:] = 0
    options.geomgroup[5] = 1
    try:
        model.geom_group[:] = 0
        model.geom_group[members] = 5
        renderer.renderer.update_scene(env.mj_data, 'cam', scene_option=options)
        segmentation = renderer.renderer.render()
        return ((segmentation[..., 0] >= 0)
                & (segmentation[..., 1] == int(mujoco.mjtObj.mjOBJ_GEOM)))
    finally:
        model.geom_group[:] = original


def object_metrics(full_mask, outline):
    """轮廓外的零散错误ID不构成该物体的真实可见面积。"""
    row = mask_metrics(np.asarray(full_mask, bool) & np.asarray(outline, bool))
    row['isolated_pixels'] = int(np.count_nonzero(outline))
    return row


def measure(env, renderer, framing):
    roots = renderer.root_map(env.mj_data)
    rows = {}
    for name in REQUIRED:
        body = env.mj_model.body(name).id
        rows[name] = object_metrics(roots == body, isolated_mask(env, renderer, name))
        rows[name]['framed'] = framing['bodies'][name]['passed']
    return dict(measurements=rows, gate=frame_gate(rows)), roots
