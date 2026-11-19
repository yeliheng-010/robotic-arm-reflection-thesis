"""在观测物体内部确定性扩展抓点，保留原候选和位移界限。"""
from itertools import product
import numpy as np
import spatialmath as sm
from top_runtime import candidates as original, MAX_TRANSLATION_M

DEPTHS_M = (.030, .020, .015)
SHIFTS = (0., -.5, .5, -1., 1.)
MAX_SHIFT_M = .020
MAX_LENGTH_FRACTION = .20
MAX_CANDIDATES = 30


def valid(fitted):
    if not fitted.get('available'):
        return False
    center = np.asarray(fitted.get('center', []), dtype=float)
    axis = np.asarray(fitted.get('closing_axis', []), dtype=float)
    if center.shape != (3,) or axis.shape != (3,):
        return False
    values = [*center, *axis, fitted['top_z_m'], fitted['width_m'], fitted['length_m']]
    return bool(np.isfinite(values).all() and fitted['width_m'] > 0 and fitted['length_m'] > 0
                and np.linalg.norm(axis[:2]) > 0 and abs(axis[2]) < 1e-12)


def candidates(nominal, fitted):
    if not valid(fitted):
        return []
    rows = original(nominal, fitted)
    seen = {tuple(np.round(r['pose'].A.flatten(), 12)) for r in rows}
    axis = np.asarray(fitted['closing_axis'], dtype=float)
    axis /= np.linalg.norm(axis)
    long_axis = np.array([-axis[1], axis[0], 0.])
    distance = min(MAX_SHIFT_M, MAX_LENGTH_FRACTION*fitted['length_m'])
    for depth, shift, sign in product(DEPTHS_M, SHIFTS, (1, -1)):
        center = np.asarray(fitted['center'], dtype=float)+shift*distance*long_axis
        center[2] = fitted['top_z_m']-depth
        if np.linalg.norm(center-nominal.t) > MAX_TRANSLATION_M:
            continue
        pose = sm.SE3.Rt(sm.SO3.TwoVectors(x=[0.,0.,-1.], y=sign*axis), center)
        key = tuple(np.round(pose.A.flatten(), 12))
        if key in seen:
            continue
        seen.add(key)
        rows.append(dict(id=f'observed_clear_d{depth}_s{shift}_f{sign}', pose=pose))
    assert len(rows) <= MAX_CANDIDATES
    return rows
