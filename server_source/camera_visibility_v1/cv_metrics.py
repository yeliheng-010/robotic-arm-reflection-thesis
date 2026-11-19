"""用同相机的隔离轮廓测遮挡，机器人和背景都保留为遮挡物。"""
import cv2
import numpy as np
from sd_render import isolated_count
from cv_policy import REQUIRED, frame_gate


def mask_metrics(mask):
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return dict(pixels=0, short_side=0, largest_component=0)
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    largest = int(stats[1:, cv2.CC_STAT_AREA].max()) if count > 1 else 0
    return dict(pixels=int(len(xs)), short_side=int(min(xs.max()-xs.min()+1,
                ys.max()-ys.min()+1)), largest_component=largest)


def measure(env, renderer, framing):
    roots = renderer.root_map(env.mj_data)
    rows = {}
    for name in REQUIRED:
        body = env.mj_model.body(name).id
        rows[name] = mask_metrics(roots == body)
        rows[name].update(isolated_pixels=isolated_count(env, renderer, name),
                          framed=framing['bodies'][name]['passed'])
    return dict(measurements=rows, gate=frame_gate(rows)), roots
