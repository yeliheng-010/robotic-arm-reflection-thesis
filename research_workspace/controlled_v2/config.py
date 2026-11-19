"""按因素独立抽样；混合组复用单因素组的同一随机实现。"""
import numpy as np
from diversity.config import SOURCES, DESTINATIONS, layout, profile, fault_parameters
from stability.collection_plan import HELDOUT

GROUPS = ('clean', 'layout', 'sensor', 'physics', 'feedback', 'mixed')
FAULTS = ('none', 'calibration', 'collision', 'placement')
PAIRS = (('RedBlock', 'BlueBin'), ('PurpleCapsule', 'RedBin'),
         ('GreenCylinder', 'SortingTray'), ('OrangeSphere', 'BlueBin'))
ARMS = ('retry', 'rule', 'flash')
VERSION = 'controlled-noise-v2'
MAX_ATTEMPTS = 3
MAX_TOKENS = 1024


def options(group):
    if group not in GROUPS:
        raise ValueError('Unknown experimental factor')
    moving, physics, sensor = (group in (key, 'mixed') for key in ('layout', 'physics', 'sensor'))
    return profile(.030 if moving else 0, 60 if moving else 0, .015 if moving else 0,
                   density=.30 if physics else 0, friction=.25 if physics else 0,
                   sigma=.003 if sensor else 0, dropout=.02 if sensor else 0, shuffle=moving)


def scenario(seed, group):
    if type(seed) is not int or seed < 0:
        raise ValueError('Expected a nonnegative integer scene seed')
    opt = options(group)
    rng = np.random.default_rng(np.random.SeedSequence([seed, 201]))
    positions, rejected = layout(rng, opt)
    yaw = rng.uniform(-opt['yaw_degrees'], opt['yaw_degrees'], len(SOURCES))*np.pi/180
    containers = {name: rng.uniform(-opt['container_xy_m'], opt['container_xy_m'], 2).tolist()
                  for name in DESTINATIONS}
    physical = np.random.default_rng(np.random.SeedSequence([seed, 202]))
    bodies = {name: dict(xy=positions[i], yaw_delta=float(yaw[i]),
                        density_scale=float(physical.uniform(1-opt['density_fraction'], 1+opt['density_fraction'])),
                        friction_scale=float(physical.uniform(1-opt['friction_fraction'], 1+opt['friction_fraction'])))
              for i, name in enumerate(SOURCES)}
    noisy = group in ('feedback', 'mixed')
    feedback = dict(mode='simulated_measurement' if noisy else 'ideal_measurement',
                    residual_sigma_m=.005 if noisy else 0, missing_probability=.15 if noisy else 0)
    return dict(version=VERSION, seed=seed, level=group, profile=opt, bodies=bodies,
                containers=containers, faults=fault_parameters(seed), feedback=feedback,
                layout_rejections=rejected, residual_source='simulation_ground_truth_evaluator_only')


def tasks(*, expanded=False):
    result = []
    for index, (source, destination) in enumerate(PAIRS if expanded else PAIRS[:2]):
        assert HELDOUT.get((source, destination), 'train') == 'train'
        for replicate in range(2 if expanded else 1):
            seed = 82000 + index*100 + replicate
            result.extend(dict(source=source, destination=destination, fault=fault, seed=seed,
                               split='train', level=group) for fault in FAULTS for group in GROUPS)
    return result
