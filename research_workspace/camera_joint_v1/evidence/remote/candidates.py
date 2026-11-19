"""固定局部方向和解析视场；原相机范围不变。"""
from itertools import product
import numpy as np
from coverage_repair_v1.proposals import changed
from sf_camera import corners, project
from camera_joint_v1.policy import fovy_for_pixels, score, ANCHORS


def offsets():
    result = [np.zeros(6)]
    for index, steps in ((0, (5., 10., 20.)), (1, (2., 5., 10.)),
                         (2, (.04, .08)), (4, (.03, .06)), (5, (.03, .06))):
        for step in steps:
            for sign in (1., -1.):
                value = np.zeros(6)
                value[index] = sign * step
                result.append(value)
    result.extend(np.array([a, b, c, 0, 0, 0])
                  for a, b, c in product((-10., 10.), (-5., 5.), (0., .04)))
    return result[:32]


def snug(camera, boxes):
    points = np.vstack([corners(box) for box in boxes.values()])
    pixels, depth = project(points, camera)
    if not np.isfinite(depth).all() or np.any(depth <= 0):
        return None
    fovy = fovy_for_pixels(camera, pixels)
    return dict(camera, fovy=fovy) if fovy is not None else None


def local(rows, boxes):
    anchors = sorted([r for r in rows if 'gate' in r], key=score)[:ANCHORS]
    bounds = np.asarray(list(boxes.values()))
    center = (bounds[:, 0].min(axis=0) + bounds[:, 1].max(axis=0)) / 2
    for offset_index, delta in enumerate(offsets()):
        for anchor in anchors:
            camera = changed(anchor['camera'], delta, center)
            camera = snug(camera, boxes) if camera is not None else None
            yield dict(camera=camera, anchor_index=anchor['index'], offset_index=offset_index,
                       delta=delta.tolist(), reason=None if camera else 'camera_bounds_or_framing_infeasible')
