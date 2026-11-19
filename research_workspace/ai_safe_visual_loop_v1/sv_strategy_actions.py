from copy import deepcopy
from unittest.mock import patch
import decision
from contracts import require
from f_response import validate as parse_response
from sv_actions import check as original_check
from live_budget import apply_action
from loopstudy.actions import validate as validate_state

STRATEGY_ACTION = 'SET_GRASP_STRATEGY'
TOP = 'observed_top'


def check(action, request):
    if not isinstance(action, dict) or action.get('id') != STRATEGY_ACTION:
        return original_check(action, request)
    require(set(action) == {'id','args'}, 'Invalid action shape')
    require(action['args'] == dict(value=TOP), 'Unsupported strategy')
    require(sum(r['id'] == STRATEGY_ACTION for r in request['actions']) == 1, 'Unavailable action')
    require(request['budget']['executions_remaining'] > 0, 'Execution budget exhausted')
    require(request['state']['grasp_strategy'] == 'original', 'Strategy already active')


def validate(response, request, *, mode):
    with patch.object(decision, 'check', check):
        return parse_response(response, request, mode=mode)


def apply(step, action):
    strategy = step['strategy']
    if action['id'] == STRATEGY_ACTION:
        assert strategy == 'original' and action['args'] == dict(value=TOP)
        state = deepcopy(step['state'])
        state['parameters']['grasp_offset'] = [0.,0.,0.]
        return validate_state(state), TOP
    assert not (strategy == TOP and action['id'] == 'SET_GRASP_OFFSET')
    return apply_action(step['state'], action), strategy


def choose(request):
    allowed = {r['id'] for r in request['actions']}
    frames = next(r['value'] for r in request['evidence'] if r['field'] == 'rgbd_surface_observations')
    unknown = any(v['status'] == 'insufficient_visible_depth' for v in frames[-1]['observed'].values())
    if unknown and 'OBSERVE' in allowed:
        return dict(id='OBSERVE', args={})
    if STRATEGY_ACTION in allowed:
        return dict(id=STRATEGY_ACTION, args=dict(value=TOP))
    if 'SET_TIME_SCALE' in allowed and request['state']['time_scale'] < 3.:
        return dict(id='SET_TIME_SCALE', args=dict(value=3.))
    return dict(id='RETRY' if 'RETRY' in allowed else 'STOP', args={})
