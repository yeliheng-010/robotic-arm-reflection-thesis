"""用独立随机流生成可复现场景，不使用测试集内容。"""
import math
import numpy as np
from stability.collection_plan import HELDOUT

SOURCES = ('RedBlock', 'GreenCylinder', 'PurpleCapsule', 'OrangeSphere')
DESTINATIONS = ('BlueBin', 'RedBin', 'SortingTray')
FAULTS = ('none', 'calibration', 'collision', 'placement')
SLOTS = ((1.08, .50), (1.08, .72), (1.25, .46), (1.47, .45))
RADII = (.050, .030, .080, .032)
MAX_LAYOUT_TRIES = 512
MIN_CLEARANCE = .008
TABLE_BOUNDS = (.85, 1.60, .39, .95)


def profile(xy, yaw, container, *, density, friction, sigma, dropout, shuffle=False):
    return dict(xy_m=xy, yaw_degrees=yaw, container_xy_m=container,
                density_fraction=density, friction_fraction=friction,
                depth_sigma_m=sigma, dropout=dropout, shuffle=shuffle)


PROFILES = {
    'clean': profile(0, 0, 0, density=0, friction=0, sigma=0, dropout=0),
    'light': profile(.015, 15, .008, density=.15, friction=.10, sigma=.001, dropout=.005),
    'medium': profile(.030, 60, .015, density=.30, friction=.25, sigma=.003, dropout=.02, shuffle=True),
    'strong': profile(.045, 120, .025, density=.45, friction=.40, sigma=.005, dropout=.05, shuffle=True),
}


def valid_layout(positions):
    xlo, xhi, ylo, yhi = TABLE_BOUNDS
    for i, ((x, y), radius) in enumerate(zip(positions, RADII)):
        if not (xlo+radius <= x <= xhi-radius and ylo <= y <= yhi-radius):
            return False
        if y-radius <= .355+.012+MIN_CLEARANCE:
            return False
        for j in range(i):
            if np.linalg.norm(np.asarray(positions[i])-positions[j]) < radius+RADII[j]+MIN_CLEARANCE:
                return False
    return True


def layout(rng, options):
    if options['xy_m'] == 0:
        return [list(p) for p in SLOTS], 0
    for rejected in range(MAX_LAYOUT_TRIES):
        slots = np.asarray(SLOTS)[rng.permutation(4)] if options['shuffle'] else np.asarray(SLOTS)
        positions = slots+rng.uniform(-options['xy_m'], options['xy_m'], (4, 2))
        if valid_layout(positions):
            return positions.tolist(), rejected
    raise ValueError('No collision-clear layout found within fixed budget')


def fault_parameters(seed):
    rng = np.random.default_rng(np.random.SeedSequence([seed, 101]))
    angle, distance = rng.uniform(-math.pi, math.pi), rng.uniform(.025, .065)
    place_angle, place_distance = rng.uniform(-math.pi, math.pi), rng.uniform(.10, .18)
    return dict(grasp_bias=[distance*math.cos(angle), distance*math.sin(angle), 0.],
                place_bias=[place_distance*math.cos(place_angle), place_distance*math.sin(place_angle), 0.],
                divider_halfheight=float(rng.uniform(.14, .21)))


def scenario(seed, level):
    if type(seed) is not int or seed < 0 or level not in PROFILES:
        raise ValueError('Expected nonnegative integer seed and a known profile')
    options = PROFILES[level]
    rng = np.random.default_rng(np.random.SeedSequence([seed, 201]))
    positions, rejected = layout(rng, options)
    bodies = {}
    for i, name in enumerate(SOURCES):
        bodies[name] = dict(xy=positions[i],
            yaw_delta=float(rng.uniform(-options['yaw_degrees'], options['yaw_degrees'])*math.pi/180),
            density_scale=float(rng.uniform(1-options['density_fraction'], 1+options['density_fraction'])),
            friction_scale=float(rng.uniform(1-options['friction_fraction'], 1+options['friction_fraction'])))
    containers = {name: rng.uniform(-options['container_xy_m'], options['container_xy_m'], 2).tolist()
                  for name in DESTINATIONS}
    return dict(version='domain-randomization-v1', seed=seed, level=level, profile=options.copy(),
                bodies=bodies, containers=containers, faults=fault_parameters(seed),
                layout_rejections=rejected, residual_source='simulation_ground_truth')


def task_matrix(*, seeds_per_group=1):
    tasks = []
    for source in SOURCES:
        for destination in DESTINATIONS:
            split = HELDOUT.get((source, destination), 'train')
            if split == 'test':
                continue
            for offset in range(seeds_per_group):
                seed = (61000 if split == 'train' else 71000)+offset
                tasks.extend(dict(source=source, destination=destination, fault=fault,
                                  seed=seed, split=split, level=level)
                             for fault in FAULTS for level in PROFILES)
    return tasks


def pilot_tasks():
    destinations = ('BlueBin', 'SortingTray', 'RedBin', 'BlueBin')
    return [dict(source=source, destination=destinations[i], fault=fault, seed=61000+i,
                 split='train', level=level)
            for i, (source, fault) in enumerate(zip(SOURCES, ('calibration', 'collision', 'placement', 'none')))
            for level in ('medium', 'clean', 'light', 'strong')]
