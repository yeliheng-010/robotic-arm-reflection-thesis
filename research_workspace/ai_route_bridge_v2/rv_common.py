from pathlib import Path
from copy import deepcopy
from reflection.__main__ import bootstrap
bootstrap()
from rb_common import read, save, sha, verify as verify_parent
from loopstudy.actions import validate

ROOT = Path(__file__).resolve().parent
SEEDS = (962501, 962502)


def change(state, control, *, action):
    value, selected = deepcopy(state), deepcopy(control)
    if action == 'SAFE_ROUTE':
        value['parameters'].update(replan=True, lift_height=.15)
    elif action == 'WORLD_DOWN_ROUTE':
        assert value['parameters']['replan']
        selected['grasp_mode'] = 'world_down'
    else:
        raise ValueError('Unregistered engineering action')
    return validate(value), selected


def verify():
    manifest = read(ROOT/'manifest.json')
    assert all(sha(p) == h for p, h in manifest['identities'].items())
    verify_parent()
    return manifest
