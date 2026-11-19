"""仅缩短JSON浮点表示，点数和完整精度规划输入保持不变。"""
from copy import deepcopy
import json

DECIMALS = 5
MAX_ABSOLUTE_ERROR = .0000051


def rounded(value, errors):
    if type(value) is float:
        result = round(value, DECIMALS)
        errors.append(abs(result-value))
        return result
    if type(value) is list:
        return [rounded(item, errors) for item in value]
    if type(value) is dict:
        return {key: rounded(item, errors) for key, item in value.items()}
    return value


def compact(request):
    result, errors = deepcopy(request), []
    body = json.loads(request['messages'][1]['content'])
    updated = rounded(body, errors)
    assert max(errors, default=0) <= MAX_ABSOLUTE_ERROR
    result['messages'][1]['content'] = json.dumps(updated, ensure_ascii=False, separators=(',', ':'))
    return result, dict(decimals=DECIMALS, maximum_absolute_rounding_error=max(errors, default=0),
        target_points=len(updated['observation']['target_points_world']),
        scene_points=len(updated['observation']['non_target_points_world']),
        dropped_points=0, silent_truncation=False, full_precision_planner_input_unchanged=True)
