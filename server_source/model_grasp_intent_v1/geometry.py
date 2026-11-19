"""仅生成候选；不把点云跨度或空白区域当作物理安全证明。"""
import numpy as np
from observed_top_pose_v1.top_fit import estimate
from natural_grasp_span_audit_v1.span import span
from model_grasp_intent_v1.contract import validate_action

MAX_TRANSLATION_M = .050
MAX_SHIFT_M, MAX_LENGTH_FRACTION = .020, .20
MAX_WIDTH_M, WIDTH_MARGIN_M = .080, .012
AXIS_EPSILON = 1e-9
REGIONS = dict(center=0, long_negative=-1, long_positive=1)


def reject(reason):
    return dict(status='rejected', reason=reason, full_path_verified=False)


def rotation(fitted, args):
    tilt, azimuth = np.deg2rad([args['tilt_deg'], args['azimuth_deg']])
    # x 为朝目标运动的方向；y 为夹爪闭合轴。方位角按世界坐标 +X 向 +Y 增大。
    approach = np.array([np.sin(tilt)*np.cos(azimuth),
                         np.sin(tilt)*np.sin(azimuth), -np.cos(tilt)])
    short = np.asarray(fitted['closing_axis'])
    closing = short - np.dot(short, approach)*approach
    if np.linalg.norm(closing) < AXIS_EPSILON:
        return None
    closing /= np.linalg.norm(closing)
    if args['symmetry_deg'] == 180:
        closing = -closing
    return np.column_stack((approach, closing, np.cross(approach, closing)))


def position(fitted, args):
    short = np.asarray(fitted['closing_axis'])
    long_axis = np.array([-short[1], short[0], 0.])
    shift = min(MAX_SHIFT_M, MAX_LENGTH_FRACTION*fitted['length_m'])
    center = np.array(fitted['center']) + REGIONS[args['region']]*shift*long_axis
    center[2] = fitted['top_z_m'] - args['depth_mm']/1000
    return center


def propose(points, nominal, action):
    action = validate_action(action)
    if action['id'] != 'PROPOSE_GRASP':
        raise ValueError('grasp_intent_required')
    fitted = estimate(points)
    if not fitted['available']:
        return reject('insufficient_observed_geometry')
    nominal = np.asarray(nominal, dtype=float)
    if nominal.shape != (3,) or not np.isfinite(nominal).all():
        raise ValueError('invalid_nominal')
    center = position(fitted, action['args'])
    if np.linalg.norm(center-nominal) > MAX_TRANSLATION_M:
        return reject('translation_limit')
    basis = rotation(fitted, action['args'])
    if basis is None:
        return reject('degenerate_closing_axis')
    width = span(points, basis[:, 1]) + WIDTH_MARGIN_M
    if width > MAX_WIDTH_M:
        return reject('observed_span')
    pose = np.eye(4)
    pose[:3, :3], pose[:3, 3] = basis, center
    return dict(status='proposal', pose=pose.tolist(), required_width_m=width,
                full_path_verified=False, action=action)
