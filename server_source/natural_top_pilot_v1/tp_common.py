from pathlib import Path
from copy import deepcopy
from f_common import read, save, sha
from loopstudy.actions import validate

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'natural_top_preflight_v1'
ACTIONS = ('USE_OBSERVED_TOP', 'SLOW_3X')


def change(state, strategy, *, action):
    value = deepcopy(state)
    assert value['parameters']['grasp_offset'] == [0.,0.,0.]
    if action == ACTIONS[0]:
        assert strategy == 'original'
        strategy = 'observed_top'
    elif action == ACTIONS[1]:
        assert strategy == 'observed_top' and value['parameters']['time_scale'] == 1.5
        value['parameters']['time_scale'] = 3.
    else:
        raise ValueError('Unregistered action')
    return validate(value), strategy


def verify():
    manifest = read(ROOT/'manifest.json')
    assert all(sha(p) == h for p,h in manifest['identities'].items())
    return manifest
