"""确定性两段归位候选；每关节始终位于原起终点范围内。"""
import math
from itertools import combinations

JOINT_COUNT = 6
JOINT_ORDER = (5, 4, 3, 2, 1, 0)


def candidates(start, goal, *, duration):
    start, goal = list(start), list(goal)
    if len(start) != JOINT_COUNT or len(goal) != JOINT_COUNT:
        raise ValueError('Expected six joints')
    if not all(math.isfinite(x) for x in [*start, *goal, duration]) or duration <= 0:
        raise ValueError('Finite joints and positive duration required')
    rows = [dict(id='direct', waypoints=[start, goal], durations=[duration])]
    seen = {tuple(start), tuple(goal)}
    for size in range(1, JOINT_COUNT):
        for indices in combinations(JOINT_ORDER, size):
            middle = [goal[i] if i in indices else start[i] for i in range(JOINT_COUNT)]
            if tuple(middle) not in seen:
                seen.add(tuple(middle))
                name = 'home_first_'+'_'.join(map(str, indices))
                rows.append(dict(id=name, waypoints=[start, middle, goal], durations=[duration, duration]))
    return rows


def first_approved(options, inspect):
    rows = []
    for option in options:
        result = inspect(option)
        rows.append(dict(candidate=option, check=result))
        if result.get('feasible') is True:
            return option, rows
    return None, rows
