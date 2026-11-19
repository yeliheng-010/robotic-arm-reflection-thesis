"""原型独立约束；不修改旧Parameters或执行器的共享定义。"""
import math

MAX_ATTEMPTS = 3
MAX_OBSERVATIONS = 2
MAX_OFFSET_M = .25
MAX_DELTA_M = .01
MAX_TIME_SCALE = 3.
PARAMETERS = ('replan', 'reground', 'lift_height', 'time_scale',
              'grasp_offset', 'place_offset', 'candidate_index')
ACTIONS = ('move_to_grasp_pose', 'close_gripper', 'move_to_point', 'open_gripper', 'back_to_zero')
SEGMENTS = ('pregrasp', 'approach', 'grasp', 'lift', 'transport', 'descent', 'retract', 'return_home')
DESCRIPTIONS = {
    'STOP': '停止本轨迹，不增加预算。',
    'OBSERVE': '获取一次已登记的额外观测；扣1观测预算，不保证信息充分。',
    'RETRY': '按当前参数重试；扣1执行预算，不保证成功。',
    'SET_TIME_SCALE': '设定整体运动时间倍率为1至3；扣1执行预算。',
    'SET_GRASP_OFFSET': '仅将一个抓取偏移坐标增减不超过10 mm；扣1执行预算。',
    'SELECT_GRASP': '选择本次感知提供的一个抓取候选索引；扣1执行预算。',
}
ARGUMENTS = {
    'STOP': {}, 'OBSERVE': {}, 'RETRY': {},
    'SET_TIME_SCALE': {'value': 'number in [1,3]'},
    'SET_GRASP_OFFSET': {'delta_m': 'three finite numbers; exactly one nonzero axis; abs <= 0.01 m; resulting offset abs <= 0.25 m'},
    'SELECT_GRASP': {'index': 'integer in [0,count) for this observation'},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def vector(value, *, size=3):
    return isinstance(value, list) and len(value) == size and all(number(v) for v in value)


def parameters(raw):
    require(isinstance(raw, dict) and set(PARAMETERS) <= set(raw), 'Incomplete parameters')
    result = {key: raw[key] for key in PARAMETERS}
    require(all(type(result[k]) is bool for k in ('replan', 'reground')), 'Bad boolean command')
    require(all(number(result[k]) for k in ('lift_height', 'time_scale')), 'Bad command value')
    require(all(vector(result[k]) for k in ('grasp_offset', 'place_offset')), 'Bad command vector')
    require(type(result['candidate_index']) is int and result['candidate_index'] >= 0, 'Bad index')
    return result
