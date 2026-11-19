"""保留冻结残差/边界，增加轴向及短长度初始化；仅接收观测点。"""
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import cKDTree
from held_observation_v1.geometry import MIN_VARIANCE, direction, residual

RADIUS_INITIAL_RANGE = (.010, .045)
HALF_INITIAL_RANGE = (.025, .12)
RADIUS_BOUNDS = (.006, .080)
HALF_BOUNDS = (.015, .150)
CENTER_MARGIN_M = .10
DIRECTION_BOUND = 2.
LOSS_SCALE_M = .003
MAX_EVALUATIONS = 150
AXIAL_SHIFT_FRACTIONS = (-.25, 0., .25)
HALF_SCALES = (.5, .75)
MIN_POINTS = 128
NEIGHBORS = 6
ISOLATION_FACTOR = 4.
MAX_REMOVAL_FRACTION = .05


def initialize(points):
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 128 or not np.isfinite(points).all():
        raise ValueError("insufficient_or_nonfinite_points")
    center = np.median(points, axis=0)
    values, basis = np.linalg.eigh(np.cov(points.T))
    if values[0] < MIN_VARIANCE:
        raise ValueError("degenerate_surface")
    basis = basis[:, ::-1]
    relative = points - center
    radius = float(np.clip(np.percentile(np.linalg.norm(relative @ basis[:, 1:], axis=1), 40),
                           *RADIUS_INITIAL_RANGE))
    extent = np.ptp(np.percentile(relative @ basis[:, 0], [5, 95]))
    half = float(np.clip(extent / 2 - radius / 2, *HALF_INITIAL_RANGE))
    return center, basis, radius, half, extent


def starts(center, basis, *, radius, half, extent):
    shifts = [np.zeros(3), radius * basis[:, 1] / 2, -radius * basis[:, 1] / 2,
              radius * basis[:, 2] / 2, -radius * basis[:, 2] / 2]
    initial = [[*(center + shift), 0., 0., radius, half] for shift in shifts]
    for scale in HALF_SCALES:
        for fraction in AXIAL_SHIFT_FRACTIONS:
            length = max(HALF_BOUNDS[0], half * scale)
            initial.append([*(center + fraction * extent * basis[:, 0]), 0., 0., radius, length])
    return initial


def fit_multistart(points):
    center, basis, radius, half, extent = initialize(points)
    low = [*(points.min(axis=0) - CENTER_MARGIN_M), -DIRECTION_BOUND, -DIRECTION_BOUND,
           RADIUS_BOUNDS[0], HALF_BOUNDS[0]]
    high = [*(points.max(axis=0) + CENTER_MARGIN_M), DIRECTION_BOUND, DIRECTION_BOUND,
            RADIUS_BOUNDS[1], HALF_BOUNDS[1]]
    trials = []
    for initial in starts(center, basis, radius=radius, half=half, extent=extent):
        trials.append(least_squares(residual, initial, args=(points, basis), bounds=(low, high),
                      loss="soft_l1", f_scale=LOSS_SCALE_M, max_nfev=MAX_EVALUATIONS))
    # 沿用最低目标函数值选解，不利用真值或质量通过与否挑选结果。
    best = min(trials, key=lambda row: row.cost)
    params = best.x
    singular = np.linalg.svd(best.jac, compute_uv=False)
    return dict(center=params[:3].tolist(), axis=direction(params, basis).tolist(),
                radius=float(params[5]), half_length=float(params[6]),
                p95_m=float(np.percentile(np.abs(residual(params, points, basis)), 95)),
                converged=bool(best.success), condition=float(singular[0] / max(singular[-1], 1e-15)))


def observed_inliers(points):
    points = np.asarray(points, dtype=float)
    initialize(points)
    distances, _ = cKDTree(points).query(points, k=NEIGHBORS + 1)
    cutoff = ISOLATION_FACTOR * float(np.median(distances[:, -1]))
    keep = distances[:, -1] <= cutoff
    if sum(keep) < MIN_POINTS or np.mean(~keep) > MAX_REMOVAL_FRACTION:
        raise ValueError("excessive_isolation_or_insufficient_points")
    return points[keep], dict(input_points=len(points), kept_points=int(sum(keep)),
                              removed_points=int(sum(~keep)), cutoff_m=cutoff)


def fit(points):
    filtered, filtering = observed_inliers(points)
    return dict(fit_multistart(filtered), filtering=filtering)
