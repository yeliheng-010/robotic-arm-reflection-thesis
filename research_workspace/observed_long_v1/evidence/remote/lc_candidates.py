"""细长物体的观测内长轴候选。"""
from unittest.mock import patch
import numpy as np
import cp_candidates
from yc_candidates import candidates as original

MIN_ASPECT = 3.
MAX_SHIFT_M = .035
LENGTH_FRACTION = .30
MAX_CANDIDATES = 180


def candidates(nominal, fitted):
    rows = original(nominal,fitted)
    if not rows or fitted['length_m']/fitted['width_m'] < MIN_ASPECT:
        return rows
    seen = {tuple(np.round(r['pose'].A.flatten(),12)) for r in rows}
    with patch.object(cp_candidates,'MAX_SHIFT_M',MAX_SHIFT_M), \
         patch.object(cp_candidates,'MAX_LENGTH_FRACTION',LENGTH_FRACTION):
        expanded = original(nominal,fitted)
    for row in expanded:
        key = tuple(np.round(row['pose'].A.flatten(),12))
        if key not in seen:
            rows.append(dict(row,id='observed_long_'+row['id']))
            seen.add(key)
    assert len(rows) <= MAX_CANDIDATES
    return rows
