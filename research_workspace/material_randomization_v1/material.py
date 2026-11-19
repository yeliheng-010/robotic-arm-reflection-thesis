"""未接入采集的独立材料能力；只修改当前进程的MjSpec。"""
import math
import numpy as np

STREAM = 966701
DENSITY_RANGE = (.7, 1.5)
PAD_RANGE = (.65, 1.15)
OBJECT_GEOMS = ('red_block', 'green_cylinder', 'purple_capsule', 'orange_sphere')
PADS = ('right_pad1', 'right_pad2', 'left_pad1', 'left_pad2')


def sample(seed, group):
    assert type(seed) is int and seed >= 0
    assert group in ('baseline', 'varied_noisy')
    if group == 'baseline':
        return {}
    rng = np.random.default_rng(np.random.SeedSequence([seed, STREAM]))
    return dict(density_multipliers={name: float(rng.uniform(*DENSITY_RANGE)) for name in OBJECT_GEOMS},
        pad_sliding_multiplier=float(rng.uniform(*PAD_RANGE)))


def validate(settings):
    assert set(settings) == {'density_multipliers', 'pad_sliding_multiplier'}
    assert set(settings['density_multipliers']) == set(OBJECT_GEOMS)
    for value in settings['density_multipliers'].values():
        assert type(value) in (float, int) and math.isfinite(value) and DENSITY_RANGE[0] <= value <= DENSITY_RANGE[1]
    value = settings['pad_sliding_multiplier']
    assert type(value) in (float, int) and math.isfinite(value) and PAD_RANGE[0] <= value <= PAD_RANGE[1]


def apply(spec, settings):
    if not settings:
        return
    validate(settings)
    for name, multiplier in settings['density_multipliers'].items():
        geom = spec.geom(name)
        assert geom.density > 0
        geom.density *= multiplier
    for name in PADS:
        geom = spec.geom(name)
        assert geom.priority == 1
        friction = np.asarray(geom.friction).copy()
        friction[0] *= settings['pad_sliding_multiplier']
        geom.friction = friction
