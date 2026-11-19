"""深度单位为米；只污染传感输入，不改物理状态和验收结果。"""
import numpy as np

DEPTH_FLOOR = .001
GAUSSIAN_CLIP_SIGMAS = 3.


def corrupt_depth(depth, options, *, seed):
    result = depth.copy()
    valid = np.isfinite(depth) & (depth > 0)
    count = int(valid.sum())
    stats = dict(valid_pixels=count, dropped_pixels=0, dropout_fraction=0., noise_rmse_m=0.)
    sigma, probability = options['depth_sigma_m'], options['dropout']
    if not (0 <= sigma <= .02 and 0 <= probability < 1):
        raise ValueError('Noise parameters outside supported bounds')
    if not count or (sigma == 0 and probability == 0):
        return result, stats
    rng = np.random.default_rng(seed)
    error = np.clip(rng.normal(0, sigma, count), -GAUSSIAN_CLIP_SIGMAS*sigma, GAUSSIAN_CLIP_SIGMAS*sigma)
    dropped = rng.random(count) < probability
    values = np.maximum(DEPTH_FLOOR, depth[valid]+error)
    values[dropped] = 0
    result[valid] = values
    realized = result[valid][~dropped]-depth[valid][~dropped]
    stats.update(dropped_pixels=int(dropped.sum()), dropout_fraction=float(dropped.mean()),
                 noise_rmse_m=float(np.sqrt(np.mean(realized**2))) if realized.size else 0.)
    return result, stats
