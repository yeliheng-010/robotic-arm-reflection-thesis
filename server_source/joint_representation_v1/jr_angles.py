"""枚举真实关节范围内的等价角，不改变末端位姿。"""
import math
from itertools import product

PERIOD = 2*math.pi


def allowed(value, limits):
    low,high = limits
    if not low < high:
        raise ValueError('Invalid joint limits')
    lower = math.ceil((low-value)/PERIOD)
    upper = math.floor((high-value)/PERIOD)
    return [value+k*PERIOD for k in range(lower,upper+1)]


def candidates(start, goal, *, bounds):
    if not start or len(start) != len(goal) or len(start) != len(bounds):
        raise ValueError('Mismatched dimensions')
    values = [*start,*goal,*[v for pair in bounds for v in pair]]
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Finite joint values required')
    choices = [allowed(value,limits) for value,limits in zip(goal,bounds)]
    return sorted([list(row) for row in product(*choices)],key=lambda row: math.dist(start,row))
