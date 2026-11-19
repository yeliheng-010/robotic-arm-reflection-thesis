from pathlib import Path
from copy import deepcopy
from rv_common import read, save, sha, verify as verify_parent
from loopstudy.actions import validate

ROOT = Path(__file__).resolve().parent
SEEDS = (962601, 962602)
LIFT_M, SLOW_SCALE, LOWER_M = .15, 1.5, .015
ACTIONS = ('SELF_SAFE_ROUTE', 'LOWER_GRASP')


def change(state, control, *, action):
    value, selected = deepcopy(state), deepcopy(control)
    if action == ACTIONS[0]:
        value['parameters'].update(replan=True, lift_height=LIFT_M, time_scale=SLOW_SCALE)
        selected['grasp_mode'] = 'world_down'
    elif action == ACTIONS[1]:
        assert value['parameters']['replan'] and selected['grasp_mode']=='world_down'
        value['parameters']['grasp_offset'] = [0., 0., -LOWER_M]
    else:
        raise ValueError('Unregistered engineering action')
    return validate(value), selected


def verify():
    manifest = read(ROOT/'manifest.json')
    assert all(sha(p)==h for p,h in manifest['identities'].items())
    verify_parent()
    return manifest
