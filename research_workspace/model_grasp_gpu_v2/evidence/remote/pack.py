"""仅压缩模型可见输入，不改变规划点云或安全检查。"""
from copy import deepcopy
import numpy as np

POINT_LIMITS = dict(target_points_world=32, non_target_points_world=96)
DECIMALS = 6


def rounded(value):
    if isinstance(value, dict):
        return {key:rounded(item) for key,item in value.items()}
    if isinstance(value, list):
        return [rounded(item) for item in value]
    return round(value,DECIMALS) if type(value) is float else value


def pack(request):
    result = deepcopy(request)
    observation = result['observation']
    for key, maximum in POINT_LIMITS.items():
        points = observation[key]
        indices = np.linspace(0,len(points)-1,min(maximum,len(points)),dtype=int)
        observation[key] = [points[index] for index in indices]
    result['observation'] = rounded(observation)
    result['input_projection'] = dict(point_limits=POINT_LIMITS, coordinate_decimals=DECIMALS,
        limitation='Model sees a subsample; missing points are not free space. Planner uses full frozen points.')
    return result
