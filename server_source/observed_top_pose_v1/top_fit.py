"""从当前观测的水平顶面估计姿态，不读物体尺寸、真值或历史成败。"""
import numpy as np

MIN_POINTS = 64
TOP_BAND_M = .006
TOP_PERCENTILE = 90
UPPER_PERCENTILE = 99.5
RECT_PERCENTILES = (2, 98)
ANGLE_STEP_DEG = 1
GRASP_DEPTH_M = .030
MIN_EDGE_M = .015


def rectangle(points):
    origin = np.median(points, axis=0)
    centered = points-origin
    best = None
    for degree in range(0, 90, ANGLE_STEP_DEG):
        angle = np.deg2rad(degree)
        axes = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        low, high = np.percentile(centered@axes, RECT_PERCENTILES, axis=0)
        sizes = high-low
        row = dict(area=float(np.prod(sizes)), sizes=sizes, center=origin+axes@((low+high)/2), axes=axes)
        if best is None or row['area'] < best['area']:
            best = row
    return best


def estimate(points):
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < MIN_POINTS or not np.isfinite(points).all():
        return dict(available=False, reason='insufficient_or_invalid_points')
    low, high = np.percentile(points[:,2], [TOP_PERCENTILE, UPPER_PERCENTILE])
    top = points[(points[:,2] >= low-TOP_BAND_M) & (points[:,2] <= high)]
    if len(top) < MIN_POINTS:
        return dict(available=False, reason='insufficient_top_points', top_points=len(top))
    fit = rectangle(top[:,:2])
    if np.min(fit['sizes']) < MIN_EDGE_M:
        return dict(available=False, reason='degenerate_footprint', top_points=len(top))
    short = int(np.argmin(fit['sizes']))
    axis = fit['axes'][:,short]
    top_z = float(np.median(top[:,2]))
    return dict(available=True, center=[*fit['center'].tolist(), top_z-GRASP_DEPTH_M],
        closing_axis=[*axis.tolist(), 0.], width_m=float(fit['sizes'][short]),
        length_m=float(fit['sizes'][1-short]), top_z_m=top_z, top_points=len(top),
        input_points=len(points), source='observed_noisy_horizontal_top_percentile_rectangle',
        limitation='Partial top coverage and non-horizontal objects may bias pose; not physical feasibility')
