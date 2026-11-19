from pathlib import Path
from copy import deepcopy
from nc_common import read, save, sha, verify as verify_parent
from loopstudy.actions import validate

ROOT = Path(__file__).resolve().parent
SEEDS = (962401, 962402)
LIFT_M = .15
SLOW_SCALE = 1.5


def change(state, action):
    value = deepcopy(state)
    if action == 'SAFE_ROUTE':
        value['parameters'].update(replan=True, lift_height=LIFT_M)
    elif action == 'SLOW_ROUTE':
        assert value['parameters']['replan'] and value['parameters']['lift_height'] == LIFT_M
        value['parameters']['time_scale'] = SLOW_SCALE
    else:
        raise ValueError('Unregistered engineering action')
    return validate(value)


def verify():
    manifest = read(ROOT/'manifest.json')
    assert all(sha(p) == h for p, h in manifest['identities'].items())
    verify_parent()
    return manifest
