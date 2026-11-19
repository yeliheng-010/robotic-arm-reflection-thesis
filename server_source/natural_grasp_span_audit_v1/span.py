import numpy as np


def span(points, axis):
    points, axis = np.asarray(points, dtype=float), np.asarray(axis, dtype=float)
    assert points.ndim == 2 and points.shape[1] == 3 and len(points) >= 64
    assert axis.shape == (3,) and np.isfinite(points).all() and np.isfinite(axis).all()
    length = np.linalg.norm(axis)
    assert length > 1e-9
    projected = (points-np.median(points, axis=0))@(axis/length)
    low, high = np.percentile(projected, [5, 95])
    return float(high-low)


def world_points(depth, mask, calibration):
    valid = mask & np.isfinite(depth) & (depth > 0)
    v, u = np.where(valid)
    fx, fy, cx, cy = calibration['intrinsics']
    z = depth[v, u]
    camera = np.column_stack(((u-cx)*z/fx, (v-cy)*z/fy, z))
    matrix = np.asarray(calibration['transform'])
    return camera@matrix[:3, :3].T+matrix[:3, 3]
