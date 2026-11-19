"""有界全局布局提案；拒绝原因留档，不根据执行成败换种子。"""
import itertools
import numpy as np
from sd_config import MOVING, CONTAINERS

CLEARANCE = .008
XY_LOW = np.array([.85, .08])
XY_HIGH = np.array([1.55, 1.10])
LAYOUT_TRIES = 512
BODY_TRIES = 256


def box_at(name, values, geometry):
    old = np.array(geometry['boxes'][name])
    center = np.array(geometry['positions'][name])
    corners = np.array(list(itertools.product(*zip(old[0], old[1]))))-center
    angle = values['yaw_delta']
    cosine, sine = np.cos(angle), np.sin(angle)
    rotation = np.array([[cosine, -sine, 0.], [sine, cosine, 0.], [0., 0., 1.]])
    moved = corners@rotation.T + values['position']
    return np.array([moved.min(axis=0), moved.max(axis=0)])


def clear(box, others, table):
    if np.any(box[0, :2] < table[0, :2]+CLEARANCE):
        return False
    if np.any(box[1, :2] > table[1, :2]-CLEARANCE):
        return False
    return all(np.max(np.maximum(box[0]-other[1], other[0]-box[1])) >= CLEARANCE
               for other in others)


def fixed_boxes(geometry):
    return [np.array(box) for name, box in geometry['boxes'].items()
            if name not in MOVING and not name.startswith(('simple_table', 'table'))]


def proposal(name, rng, geometry):
    position = np.array(geometry['positions'][name])
    position[:2] = rng.uniform(XY_LOW, XY_HIGH)
    yaw = 0. if name in CONTAINERS else float(rng.uniform(-np.pi, np.pi))
    return dict(position=position.tolist(), yaw_delta=yaw)


def place(name, rng, *, geometry, occupied, minimum):
    table = np.array(geometry['table'])
    origin = np.array(geometry['positions'][name])
    for rejected in range(BODY_TRIES):
        value = proposal(name, rng, geometry)
        distance = float(np.linalg.norm(np.array(value['position'])[:2]-origin[:2]))
        box = box_at(name, value, geometry)
        if distance >= minimum and clear(box, occupied, table):
            return value, box, rejected, distance
    return None, None, BODY_TRIES, None


def attempt(rng, geometry, minimum):
    bodies, distances, occupied, rejected = {}, {}, fixed_boxes(geometry), 0
    for name in MOVING:
        value, box, count, distance = place(name, rng, geometry=geometry,
                                           occupied=occupied, minimum=minimum)
        rejected += count
        if value is None:
            return None, {}, rejected
        bodies[name], distances[name] = value, distance
        occupied.append(box)
    return bodies, distances, rejected


def check(bodies, geometry):
    occupied, failures = fixed_boxes(geometry), []
    for name in MOVING:
        box = box_at(name, bodies[name], geometry)
        if not clear(box, occupied, np.array(geometry['table'])):
            failures.append(name)
        occupied.append(box)
    return dict(passed=not failures, failures=failures)


def sample(seed, geometry):
    rng = np.random.default_rng(np.random.SeedSequence([seed, 960201]))
    minimum = .20 if seed % 2 == 0 else .10
    total = 0
    for count in range(LAYOUT_TRIES):
        bodies, distances, rejected = attempt(rng, geometry, minimum)
        total += rejected
        if bodies is not None:
            return dict(accepted=True, bodies=bodies, displacements=distances,
                        layout_rejections=count, body_rejections=total, minimum_move=minimum)
    return dict(accepted=False, bodies={}, displacements={},
                layout_rejections=LAYOUT_TRIES, body_rejections=total, minimum_move=minimum)
