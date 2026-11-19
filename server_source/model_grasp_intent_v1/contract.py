"""独立版本的模型动作白名单；不接受安全开关或关节角。"""
from copy import deepcopy

CHOICES = dict(region=('center', 'long_negative', 'long_positive'),
               depth_mm=(15, 20, 30), tilt_deg=(0, 15, 30, 45, 60, 90),
               azimuth_deg=tuple(range(0, 360, 45)), symmetry_deg=(0, 180))
BUDGET_CAPS = dict(decisions=8, planning=4, observations=2)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_action(action):
    require(type(action) is dict and set(action) == {'id', 'args'}, 'invalid_action')
    name, args = action['id'], action['args']
    require(name in ('PROPOSE_GRASP', 'OBSERVE', 'STOP'), 'unknown_action')
    require(type(args) is dict, 'invalid_args')
    if name != 'PROPOSE_GRASP':
        require(not args, 'unexpected_args')
        return deepcopy(action)
    require(set(args) == set(CHOICES), 'invalid_intent_fields')
    for key, values in CHOICES.items():
        expected = str if key == 'region' else int
        require(type(args[key]) is expected and args[key] in values, 'out_of_range')
    require(args['tilt_deg'] != 0 or args['azimuth_deg'] == 0, 'top_azimuth_must_be_zero')
    return deepcopy(action)


def validate_budget(budget):
    require(type(budget) is dict and set(budget) == set(BUDGET_CAPS), 'invalid_budget')
    for key, cap in BUDGET_CAPS.items():
        require(type(budget[key]) is int and 0 <= budget[key] <= cap, 'invalid_budget_value')
    return deepcopy(budget)


def validate_response(response):
    require(type(response) is dict and set(response) == {'action'}, 'invalid_response')
    return validate_action(response['action'])
