"""保留原候选，增加闭合方向；所有候选仍经过原完整场景过滤。"""
import numpy as np
from grasp_process import GraspGroup, generate_geometric_topdown_grasp as original

ANGLES_DEG = (30, 60, 90, 120, 150)
WIDTH_MARGIN = .012
MIN_WIDTH, MAX_WIDTH = .02, .08
MIN_POINTS = 64
MIN_XY_VARIANCE = 1e-12
ADDED_SCORE = .49


def validate_points(target_points):
    points = np.asarray(target_points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < MIN_POINTS:
        raise ValueError('需要至少64个三维目标点')
    if not np.isfinite(points).all():
        raise ValueError('目标点必须全部有限')
    if np.var(points[:, :2], axis=0).sum() < MIN_XY_VARIANCE:
        raise ValueError('目标点云XY方向退化')
    return points


def generate(target_points):
    points = validate_points(target_points)
    base = original(points)
    rows = [base.grasp_group_array[0].copy()]
    grasp = base[0]
    centered = points[:, :2] - grasp.translation[:2]
    for angle in ANGLES_DEG:
        radians = np.deg2rad(angle)
        cosine, sine = np.cos(radians), np.sin(radians)
        closing_xy = np.array([[cosine, -sine], [sine, cosine]]) @ grasp.rotation_matrix[:2, 1]
        span = np.diff(np.percentile(centered @ closing_xy, [5, 95]))[0]
        width = max(MIN_WIDTH, float(span) + WIDTH_MARGIN)
        if width > MAX_WIDTH:
            continue
        closing = np.r_[closing_xy, 0.]
        approach = grasp.rotation_matrix[:, 0]
        rotation = np.column_stack([approach, closing, np.cross(approach, closing)])
        row = rows[0].copy()
        row[0], row[1] = ADDED_SCORE, width
        row[4:13] = rotation.reshape(-1)
        rows.append(row)
    return GraspGroup(np.stack(rows))

