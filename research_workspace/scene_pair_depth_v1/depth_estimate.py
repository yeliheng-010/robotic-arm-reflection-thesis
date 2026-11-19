"""从含噪观测的目标内部邻域恢复缺失定位深度。"""
import math
from numbers import Real
from statistics import median, quantiles

RADIUS = 2
MIN_SUPPORT = 8
MAX_TRIMMED_SPREAD_M = .020


def coordinates(pixel, depth):
    if not isinstance(pixel, (tuple, list)) or len(pixel) != 2:
        return None
    if any(isinstance(x, bool) or not isinstance(x, Real) or not math.isfinite(x) for x in pixel):
        return None
    u, v = map(int, pixel)
    h, w = len(depth), len(depth[0])
    return (u, v) if RADIUS <= u < w-RADIUS and RADIUS <= v < h-RADIUS else None


def positive(value):
    return math.isfinite(float(value)) and value > 0


def samples(depth, mask, *, u, v):
    return [[x, y, float(depth[y][x])] for y in range(v-RADIUS, v+RADIUS+1)
            for x in range(u-RADIUS, u+RADIUS+1) if mask[y][x] and positive(depth[y][x])]


def supported(points, *, u, v):
    quadrants = {(x > u, y > v) for x, y, _ in points if x != u and y != v}
    return len(points) >= MIN_SUPPORT and len(quadrants) == 4


def estimate(depth, mask, *, pixel):
    location = coordinates(pixel, depth)
    result = dict(accepted=False, reason='invalid_or_border_pixel')
    if location is None:
        return result
    u, v = location
    result.update(pixel_uv=[u, v], reason='already_valid')
    if positive(depth[v][u]):
        return result
    result['reason'] = 'target_boundary'
    if not all(mask[y][x] for y in range(v-1, v+2) for x in range(u-1, u+2)):
        return result
    points = samples(depth, mask, u=u, v=v)
    result.update(reason='insufficient_spatial_support', support=points)
    if not supported(points, u=u, v=v):
        return result
    values = [p[2] for p in points]
    deciles = quantiles(values, n=10, method='inclusive')
    spread = deciles[-1]-deciles[0]
    result.update(reason='depth_discontinuity', trimmed_spread_m=spread)
    if spread > MAX_TRIMMED_SPREAD_M:
        return result
    return dict(result, accepted=True, reason='local_target_median', value_m=float(median(values)))
