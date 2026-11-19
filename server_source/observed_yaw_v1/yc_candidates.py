"""观测内的小角度竖直抓取候选。"""
import numpy as np
import spatialmath as sm
from cp_candidates import candidates as original

YAW_DEGREES = (-15.,15.)
MAX_CANDIDATES = 90


def candidates(nominal, fitted):
    base = original(nominal,fitted)
    rows = list(base)
    for row in base:
        for angle in YAW_DEGREES:
            rotation = sm.SO3.Rz(np.deg2rad(angle))*sm.SO3(row['pose'].R)
            pose = sm.SE3.Rt(rotation,row['pose'].t)
            rows.append(dict(id=row['id']+f'_yaw{angle}',pose=pose))
    assert len(rows) <= MAX_CANDIDATES
    return rows
