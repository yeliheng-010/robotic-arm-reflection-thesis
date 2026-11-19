"""只用原包围盒重居中/收紧视场，全部参数仍受原相机边界约束。"""
import numpy as np
from sf_camera import corners, project, framed
from coverage_repair_v1.proposals import changed
from camera_joint_v1.candidates import snug

JACOBIAN_STEP = .001
RECENTER_ITERATIONS = 2
TARGET_RANGE = .1
IMAGE_CENTER = 320.


def image_center(camera, points):
    pixels, depths = project(points, camera)
    if not np.isfinite(pixels).all() or np.any(depths <= 0):
        return None
    return (pixels.min(axis=0) + pixels.max(axis=0)) / 2


def recenter(camera, boxes, center):
    points = np.vstack([corners(b) for b in boxes.values()])
    for _ in range(RECENTER_ITERATIONS):
        current = image_center(camera, points)
        if current is None:
            return None
        columns = []
        for axis in (0, 1):
            probe = dict(camera)
            move = np.eye(3)[axis] * JACOBIAN_STEP
            probe.update(position=(np.array(camera['position'])+move).tolist(),
                         target=(np.array(camera['target'])+move).tolist())
            columns.append((image_center(probe, points)-current)/JACOBIAN_STEP)
        jacobian = np.column_stack(columns)
        if np.linalg.cond(jacobian) > 1e6:
            break
        target = np.asarray(camera['target'][:2]) + np.linalg.solve(jacobian, IMAGE_CENTER-current)
        target = np.clip(target, center[:2]-TARGET_RANGE, center[:2]+TARGET_RANGE)
        delta = np.r_[np.zeros(4), target-np.asarray(camera['target'][:2])]
        updated = changed(camera, delta, center)
        if updated is None:
            break
        camera = updated
    camera = snug(camera, boxes)
    return camera if camera is not None and framed(boxes, camera)['passed'] else None
