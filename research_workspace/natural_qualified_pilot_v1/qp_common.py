from pathlib import Path
from copy import deepcopy
from sr_common import read,save,sha,verify as verify_parent
from loopstudy.actions import validate

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'natural_feasibility_v1'
ACTIONS=('LOWER_10MM','SLOW_3X')


def change(state, control, *, action):
    value=deepcopy(state)
    assert control==dict(grasp_mode='world_down') and value['parameters']['replan']
    if action==ACTIONS[0]:
        value['parameters']['grasp_offset'][2]-=.01
    elif action==ACTIONS[1]:
        value['parameters']['time_scale']=3.
    else:
        raise ValueError('Unregistered action')
    return validate(value),deepcopy(control)


def verify():
    manifest=read(ROOT/'manifest.json')
    assert all(sha(p)==h for p,h in manifest['identities'].items())
    verify_parent()
    return manifest
