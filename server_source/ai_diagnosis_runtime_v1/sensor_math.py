"""像素与带噪深度生成可见表面统计，不接受物体真值位置。"""
import numpy as np

MIN_VALID_PIXELS = 16
MAX_POINTS = 4096


def surface(depth, mask, *, transform, intrinsics):
    if depth.shape != mask.shape or depth.ndim != 2:
        raise ValueError('Depth and mask dimensions differ')
    pixels = int(np.count_nonzero(mask))
    valid = mask & np.isfinite(depth) & (depth > 0)
    count = int(np.count_nonzero(valid))
    row = dict(visible_pixels=pixels, valid_depth_pixels=count,
               valid_depth_fraction=count/max(1, pixels),
               segmentation_source='simulation_segmentation', position_source='noisy_depth_backprojection')
    if count < MIN_VALID_PIXELS:
        return dict(row, status='insufficient_visible_depth', surface_centroid_world_m=None)
    v, u = np.nonzero(valid)
    stride = max(1, int(np.ceil(len(v)/MAX_POINTS)))
    v, u = v[::stride], u[::stride]
    z = depth[v, u]
    fx, fy, cx, cy = intrinsics
    points = np.column_stack(((u-cx)*z/fx, (v-cy)*z/fy, z))
    world = points @ np.asarray(transform)[:3, :3].T + np.asarray(transform)[:3, 3]
    low, high = np.percentile(world, [10, 90], axis=0)
    return dict(row, status='visible_surface', surface_centroid_world_m=np.median(world, axis=0).tolist(),
                surface_spread_p10_p90_m=(high-low).tolist(),
                interpretation='Visible surface statistic, not object body center or calibrated confidence')


def uniform_rows(rows, *, limit=12):
    if not rows:
        return []
    indices = np.unique(np.linspace(0, len(rows)-1, min(limit, len(rows))).astype(int))
    return [rows[int(i)] for i in indices]
