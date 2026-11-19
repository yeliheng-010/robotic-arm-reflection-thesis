"""沿用原相机变化范围，增加完整包围盒入画约束。"""
import itertools
import numpy as np
from sd_camera import look_at, BASE_POSITION, TARGET

IMAGE_SIZE = 640
PIXEL_MARGIN = 24
PROPOSAL_BUDGET = 64
STREAM = 970203


def corners(box):
    return np.array(list(itertools.product(*zip(box[0], box[1]))))


def project(points, camera):
    rotation = np.array(camera['rotation']) @ np.diag([1., -1., -1.])
    local = (np.asarray(points)-camera['position']) @ rotation
    focal = IMAGE_SIZE/(2*np.tan(np.deg2rad(camera['fovy'])/2))
    with np.errstate(divide='ignore', invalid='ignore'):
        pixels = focal*local[:, :2]/local[:, 2:3] + IMAGE_SIZE/2
    return pixels, local[:, 2]


def framed(boxes, camera):
    rows = {}
    for name, box in boxes.items():
        pixels, depth = project(corners(box), camera)
        passed = (np.isfinite(pixels).all() and np.all(depth > 0)
                  and np.all(pixels >= PIXEL_MARGIN)
                  and np.all(pixels <= IMAGE_SIZE-1-PIXEL_MARGIN))
        rows[name] = dict(passed=bool(passed), low=pixels.min(axis=0).tolist(),
                          high=pixels.max(axis=0).tolist(), min_depth=float(depth.min()))
    return dict(passed=all(row['passed'] for row in rows.values()), bodies=rows)


def proposal(seed, index, *, boxes):
    rng = np.random.default_rng(np.random.SeedSequence([seed, STREAM, index]))
    bounds = np.asarray(list(boxes.values()))
    focus = (bounds[:, 0].min(axis=0)+bounds[:, 1].max(axis=0))/2
    focus[:2] += rng.uniform(-.10, .10, 2)
    azimuth = np.pi + np.deg2rad(rng.uniform(-60., 60.))
    elevation = np.deg2rad(rng.uniform(35., 75.))
    distance = np.linalg.norm(BASE_POSITION-TARGET)*rng.uniform(.8, 1.3)
    direction = [np.cos(elevation)*np.cos(azimuth), np.cos(elevation)*np.sin(azimuth), np.sin(elevation)]
    position = focus + distance*np.array(direction)
    return dict(position=position.tolist(), target=focus.tolist(), rotation=look_at(position, focus).tolist(),
                fovy=float(rng.uniform(48., 65.)), azimuth_offset_deg=float(np.rad2deg(azimuth-np.pi)),
                elevation_deg=float(np.rad2deg(elevation)), distance_m=float(distance))
