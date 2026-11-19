"""拒绝无预算、未登记或越界提议；实际执行接线仍需独立验证。"""
from contracts import require, number, vector, MAX_OFFSET_M, MAX_DELTA_M, MAX_TIME_SCALE


def check(action, request):
    require(isinstance(action, dict) and set(action) == {'id', 'args'}, 'Invalid action shape')
    require(isinstance(action['id'], str) and isinstance(action['args'], dict), 'Bad action fields')
    choices = [r for r in request['actions'] if r['id'] == action['id']]
    require(len(choices) == 1, 'Unavailable action')
    name, args = action['id'], action['args']
    if name != 'STOP':
        require(request['budget']['executions_remaining'] > 0, 'Execution budget exhausted')
    if name == 'OBSERVE':
        require(request['budget']['observations_remaining'] > 0, 'Observation budget exhausted')
    if name in ('STOP', 'OBSERVE', 'RETRY'):
        require(not args, 'Unexpected arguments')
    else:
        check_parameters(name, args, request=request, capability=choices[0])


def check_parameters(name, args, *, request, capability):
    if name == 'SET_TIME_SCALE':
        require(set(args) == {'value'} and number(args['value']), 'Bad time scale')
        require(1. <= args['value'] <= MAX_TIME_SCALE, 'Time scale out of bounds')
    elif name == 'SELECT_GRASP':
        require(set(args) == {'index'} and type(args['index']) is int, 'Bad grasp index')
        require(0 <= args['index'] < capability['count'], 'Unavailable grasp')
    elif name == 'SET_GRASP_OFFSET':
        check_offset(args, request)
    else:
        raise ValueError('Unsupported action')


def check_offset(args, request):
    require(set(args) == {'delta_m'} and vector(args['delta_m']), 'Bad grasp delta')
    delta = args['delta_m']
    require(sum(v != 0 for v in delta) == 1, 'Exactly one changed axis required')
    require(max(abs(v) for v in delta) <= MAX_DELTA_M, 'Delta out of bounds')
    current = request['state']['grasp_offset']
    require(all(abs(a+b) <= MAX_OFFSET_M for a, b in zip(current, delta)), 'Offset out of bounds')
