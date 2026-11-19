"""单因素场景与与模型恢复率无关的资格门槛。"""
import numpy as np
from controlled.config import scenario
from diversity.config import layout

SEEDS = (905001,905002,905003)
PAIRS = (('RedBlock','BlueBin'),('PurpleCapsule','RedBin'))
FACTORS = ('position_only','yaw_only')
POSITION_M = .01
YAW_DEGREES = 12


def build(seed,factor):
    if factor not in FACTORS:
        raise ValueError('Unknown factor')
    result = scenario(seed,'clean')
    result.update(version='scene-qualification-v1',level=factor)
    if factor=='position_only':
        result['profile']['xy_m'] = POSITION_M
        rng = np.random.default_rng(np.random.SeedSequence([seed,601]))
        positions,rejections = layout(rng,result['profile'])
        for body,xy in zip(result['bodies'].values(),positions):
            body['xy'] = xy
        result['layout_rejections'] = rejections
    else:
        result['profile']['yaw_degrees'] = YAW_DEGREES
        rng = np.random.default_rng(np.random.SeedSequence([seed,602]))
        for body in result['bodies'].values():
            body['yaw_delta'] = float(rng.uniform(-YAW_DEGREES,YAW_DEGREES)*np.pi/180)
    return result


def items():
    return [dict(id=f'Q{p}_{seed}_{factor}',source=source,destination=dest,seed=seed,factor=factor)
            for p,(source,dest) in enumerate(PAIRS) for seed in SEEDS for factor in FACTORS]


def qualify(control,collision,phase,*,paired):
    return bool(control and collision and paired and phase in ('lift','transport'))
