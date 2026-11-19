"""动作枚举及有界路径选择，尚未读取任何碰撞真值。"""
from itertools import product
from model_grasp_intent_v1.contract import CHOICES, validate_action

MAX_PATH_ACTIONS = 4


def actions():
    rows = []
    for values in product(*CHOICES.values()):
        args = dict(zip(CHOICES,values))
        if args['tilt_deg']==0 and args['azimuth_deg']!=0:
            continue
        rows.append(validate_action(dict(id='PROPOSE_GRASP',args=args)))
    return rows


def select(catalogue, endpoints, *, maximum):
    if type(maximum) is not int or not 0 <= maximum <= MAX_PATH_ACTIONS:
        raise ValueError('Invalid path budget')
    safe = {row['action_id'] for row in endpoints if row['ok']}
    chosen, remaining, directions = [], [], set()
    for row in catalogue:
        if row['id'] not in safe:
            continue
        args = row['action']['args']
        key = (args['tilt_deg'],args['azimuth_deg'])
        if key in directions:
            remaining.append(row['id'])
        else:
            chosen.append(row['id'])
            directions.add(key)
    return (chosen+remaining)[:maximum]
