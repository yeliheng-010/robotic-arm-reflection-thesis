"""仅接收观测点云；目标与绕行边界不读取环境或真值尺寸。"""
import numpy as np
from scipy.spatial import ConvexHull, QhullError

TRIM = (2, 98)
FLOOR_BAND_M = .006
MIN_FLOOR_POINTS = 128
MIN_RIM_RISE_M = .025
FOOTPRINT_MARGIN_M = .020
CORRIDOR_MARGIN_M = .15
BOTTOM_GAPS_M = (.010, .040, .070)
GRID = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))
GRID_FRACTION = .25


def fits(hull, center, half):
    corners = center + np.array([[-1, -1], [-1, 1], [1, -1], [1, 1]])*half
    normal, offset = hull.equations[:, :2], hull.equations[:, 2]
    distances = corners@normal.T + offset
    return bool(np.all(distances <= -FOOTPRINT_MARGIN_M))


def support(points, anchor):
    floor = points[np.abs(points[:, 2]-anchor[2]) <= FLOOR_BAND_M]
    if len(floor) < MIN_FLOOR_POINTS:
        raise ValueError('insufficient_observed_floor')
    floor_z = float(np.median(floor[:, 2]))
    floor = points[np.abs(points[:, 2]-floor_z) <= FLOOR_BAND_M]
    low, high = np.percentile(floor[:, :2], TRIM, axis=0)
    selected = floor[np.all((floor[:, :2] >= low) & (floor[:, :2] <= high), axis=1)]
    if len(selected) < MIN_FLOOR_POINTS:
        raise ValueError('insufficient_interior_floor')
    try:
        hull = ConvexHull(selected[:, :2])
    except QhullError as error:
        raise ValueError('degenerate_observed_floor') from error
    return selected, hull, floor_z


def build(source, container, *, anchor):
    source, container, anchor = map(lambda a: np.asarray(a, float), (source, container, anchor))
    if min(len(source), len(container)) < MIN_FLOOR_POINTS:
        raise ValueError('insufficient_observed_points')
    if not all(np.isfinite(a).all() for a in (source, container, anchor)):
        raise ValueError('nonfinite_observation')
    floor, hull, floor_z = support(container, anchor)
    rim = float(np.percentile(container[:, 2], 98))
    if rim-floor_z < MIN_RIM_RISE_M:
        raise ValueError('container_rim_not_observed')
    low, high = np.percentile(source, TRIM, axis=0)
    center, half = (low+high)/2, (high-low)/2
    floor_low, floor_high = np.percentile(floor[:, :2], TRIM, axis=0)
    middle, span = (floor_low+floor_high)/2, floor_high-floor_low
    candidates = [anchor[:2]] + [middle + np.asarray(grid)*span*GRID_FRACTION for grid in GRID]
    centers = [xy.tolist() for xy in candidates if fits(hull, xy, half[:2])]
    if not centers:
        raise ValueError('observed_floor_does_not_support_object_margin')
    return dict(source_center=center.tolist(), source_half=half.tolist(), centers=centers,
        floor_z=floor_z, rim_z=rim, floor_points=len(floor), container_points=len(container),
        edges=[(np.min(container[:, :2], axis=0)-CORRIDOR_MARGIN_M).tolist(),
               (np.max(container[:, :2], axis=0)+CORRIDOR_MARGIN_M).tolist()],
        source='Predicted RGB masks and noisy depth only', full_geometry_known=False)


def targets(pose, geometry):
    offset = pose.t-np.asarray(geometry['source_center'])
    for index, xy in enumerate(geometry['centers']):
        for gap in BOTTOM_GAPS_M:
            center = np.array([*xy, geometry['rim_z']+gap+geometry['source_half'][2]])
            yield dict(id=f'observed_{index}_{gap}', target=(center+offset).tolist(),
                object_center=center.tolist(), bottom_gap=gap, grid_index=index,
                source='observed_floor_rim_and_source_extent')
