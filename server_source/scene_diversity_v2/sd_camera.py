"""MuJoCo 相机局部负 Z 轴指向目标，正 Y 轴朝上。"""
import numpy as np

EPSILON = 1e-10
TARGET = np.array([1.2, .60, .82])
BASE_POSITION = np.array([.85, .60, 1.90])


def unit(value):
    value = np.asarray(value, dtype=float)
    length = np.linalg.norm(value)
    if not np.isfinite(length) or length < EPSILON:
        raise ValueError('Degenerate camera direction')
    return value/length


def look_at(eye, target):
    backward = unit(np.asarray(eye)-target)
    reference = np.array([0., 0., 1.])
    if abs(backward@reference) > .99:
        reference = np.array([0., 1., 0.])
    right = unit(np.cross(reference, backward))
    up = np.cross(backward, right)
    return np.column_stack((right, up, backward))


def sample(seed):
    rng = np.random.default_rng(np.random.SeedSequence([seed, 960203]))
    azimuth = np.pi + np.deg2rad(rng.uniform(-60., 60.))
    elevation = np.deg2rad(rng.uniform(35., 75.))
    distance = np.linalg.norm(BASE_POSITION-TARGET)*rng.uniform(.8, 1.3)
    target = TARGET + np.r_[rng.uniform(-.10, .10, 2), 0.]
    direction = [np.cos(elevation)*np.cos(azimuth),
                 np.cos(elevation)*np.sin(azimuth), np.sin(elevation)]
    position = target + distance*np.array(direction)
    return dict(position=position.tolist(), target=target.tolist(),
                rotation=look_at(position, target).tolist(), fovy=float(rng.uniform(48., 65.)),
                azimuth_offset_deg=float(np.rad2deg(azimuth-np.pi)),
                elevation_deg=float(np.rad2deg(elevation)), distance_m=float(distance))
