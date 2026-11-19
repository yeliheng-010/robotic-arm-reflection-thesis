from pathlib import Path
from copy import deepcopy
from f_common import read, save, sha
from loopstudy.actions import validate

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'natural_span_preflight_v1'
ACTIONS = ('DEEPER_30MM', 'SLOW_3X')
DEPTH_M = -.030


def change(state, control, *, action):
    value = deepcopy(state)
    assert control == dict(grasp_mode='world_down') and value['parameters']['replan']
    if action == ACTIONS[0]:
        assert value['parameters']['grasp_offset'] == [0., 0., 0.]
        value['parameters']['grasp_offset'][2] = DEPTH_M
    elif action == ACTIONS[1]:
        assert value['parameters']['grasp_offset'] == [0., 0., DEPTH_M]
        value['parameters']['time_scale'] = 3.
    else:
        raise ValueError('Unregistered engineering action')
    return validate(value), deepcopy(control)


def verify():
    manifest = read(ROOT/'manifest.json')
    assert all(sha(p) == h for p, h in manifest['identities'].items())
    return manifest
