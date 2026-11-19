"""输入只接受已获准的数值观测；来源许可仍由真实入口审计负责。"""
from copy import deepcopy
import hashlib
import json
import numpy as np
from observed_top_pose_v1.top_fit import estimate
from model_grasp_intent_v1.contract import require

FIELDS = {'qualified', 'revision', 'target_points', 'scene_points', 'nominal'}
TARGET_SAMPLE_LIMIT, SCENE_SAMPLE_LIMIT = 128, 256
MAX_INPUT_POINTS = 200000


def cloud(value, *, minimum):
    require(type(value) is list and minimum <= len(value) <= MAX_INPUT_POINTS, 'invalid_cloud_size')
    points = np.asarray(value, dtype=float)
    require(points.ndim == 2 and points.shape[1] == 3, 'invalid_cloud_shape')
    require(np.isfinite(points).all(), 'nonfinite_cloud')
    return points


def validate(raw):
    require(type(raw) is dict and set(raw) == FIELDS, 'invalid_observation_fields')
    require(raw['qualified'] is True, 'unqualified_observation')
    require(type(raw['revision']) is int and raw['revision'] >= 0, 'invalid_revision')
    cloud(raw['target_points'], minimum=64)
    cloud(raw['scene_points'], minimum=1)
    nominal = np.asarray(raw['nominal'], dtype=float)
    require(nominal.shape == (3,) and np.isfinite(nominal).all(), 'invalid_nominal')
    return deepcopy(raw)


def fingerprint(raw):
    body = {key: raw[key] for key in sorted(FIELDS-{'revision', 'qualified'})}
    return hashlib.sha256(json.dumps(body, sort_keys=True, allow_nan=False).encode()).hexdigest()


def sample(value, maximum):
    points = cloud(value, minimum=1)
    order = np.lexsort((points[:, 2], points[:, 1], points[:, 0]))
    indices = np.linspace(0, len(points)-1, min(len(points), maximum), dtype=int)
    return points[order[indices]].tolist()


def public(raw):
    fitted = estimate(raw['target_points'])
    fit = {key: fitted[key] for key in ('available',)}
    if fitted['available']:
        keys = ('center', 'closing_axis', 'top_z_m', 'width_m', 'length_m')
        fit.update({key: fitted[key] for key in keys})
        x, y, _ = fitted['closing_axis']
        fit['long_axis'] = [-y, x, 0.]
    return dict(revision=raw['revision'], coordinate_frame='world_metres', observed_top=fit,
                target_points_world=sample(raw['target_points'], TARGET_SAMPLE_LIMIT),
                non_target_points_world=sample(raw['scene_points'], SCENE_SAMPLE_LIMIT),
                limitations='Partial noisy observations; unobserved space is unknown, not free space.')
