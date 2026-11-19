import math
from itertools import combinations
import numpy as np

THRESHOLDS=(.1,.2,.3,.4,.5,.6,.7,.8,.85,.9,.95)
MIN_ANGLE_DEG=10.
MAX_PAIRS=24
NOISE_REPEATS=3
MIN_POINTS=128


def gate_at(report,threshold,*,names=None):
    objects=report.get('gate',{}).get('objects',{})
    requested=list(objects) if names is None else list(names)
    if not requested or not 0<=threshold<=1:
        return False
    for name in requested:
        row=objects.get(name,{})
        fraction=row.get('visible_fraction',float('nan'))
        if not math.isfinite(fraction) or not 0<=fraction<=1:
            return False
        if fraction<threshold or set(row.get('reasons',['invalid']))-{'visible_fraction'}:
            return False
    return True


def angle(one,two):
    a=np.asarray(one['position'])-one['target']
    b=np.asarray(two['position'])-two['target']
    return float(np.rad2deg(np.arccos(np.clip(np.dot(a,b)/np.linalg.norm(a)/np.linalg.norm(b),-1.,1.))))


def select_pairs(rows):
    valid=[r for r in rows if r['source_pixels']>=MIN_POINTS]
    buckets={}
    for a,b in combinations(valid,2):
        if angle(a['camera'],b['camera'])<MIN_ANGLE_DEG:
            continue
        bucket=int(min(a['source_fraction'],b['source_fraction'])*10)
        buckets.setdefault(bucket,[]).append((a['index'],b['index']))
    selected=[]
    while any(buckets.values()) and len(selected)<MAX_PAIRS:
        for key in sorted(buckets):
            if buckets[key] and len(selected)<MAX_PAIRS:
                selected.append(buckets[key].pop(0))
    return selected
