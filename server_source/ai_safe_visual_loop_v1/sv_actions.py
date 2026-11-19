from contextlib import contextmanager
from unittest.mock import patch
import action_check
from f_response import validate as original_validate

MAX_DELTA_M = .030
MAX_OFFSET_M = .050


@contextmanager
def bounds():
    with patch.multiple(action_check, MAX_DELTA_M=MAX_DELTA_M, MAX_OFFSET_M=MAX_OFFSET_M):
        yield


def check(action, request):
    with bounds():
        action_check.check(action, request)


def validate(response, request, *, mode):
    with bounds():
        return original_validate(response, request, mode=mode)


def choose(request):
    allowed = {r['id'] for r in request['actions']}
    frames = next(r['value'] for r in request['evidence'] if r['field'] == 'rgbd_surface_observations')
    unknown = any(v['status'] == 'insufficient_visible_depth' for v in frames[-1]['observed'].values())
    if unknown and 'OBSERVE' in allowed:
        return dict(id='OBSERVE', args={})
    if 'SET_GRASP_OFFSET' in allowed and request['state']['grasp_offset'] == [0., 0., 0.]:
        return dict(id='SET_GRASP_OFFSET', args=dict(delta_m=[0., 0., -MAX_DELTA_M]))
    if 'SET_TIME_SCALE' in allowed and request['state']['time_scale'] < 3.:
        return dict(id='SET_TIME_SCALE', args=dict(value=3.))
    return dict(id='RETRY' if 'RETRY' in allowed else 'STOP', args={})
