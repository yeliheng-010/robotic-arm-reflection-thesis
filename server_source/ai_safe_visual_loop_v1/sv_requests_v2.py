from contextlib import contextmanager
from unittest.mock import patch
from sd_appearance import labels
from prompts import messages
import sv_requests
from sv_common import ROOT, read

original = sv_requests.build
BASE_LABELS = {'RedBlock':'红色方块', 'PurpleCapsule':'紫色胶囊', 'BlueBin':'蓝色箱子', 'RedBin':'红色箱子'}


def decorate(bundle, case):
    mapping = dict(BASE_LABELS, **labels(case['config']['appearance']))
    task = {k: mapping[case['item'][k]] for k in ('source', 'destination')}
    request = bundle['request']
    request['task_description'] = dict(source=task['source'], destination=task['destination'],
        instruction=f"将{task['source']}放入{task['destination']}",
        source_of_description='registered_task_instruction_using_scene_display_labels')
    request['execution_semantics']['object_identifiers'] = 'Task IDs remain stable across colour randomization; BlueBin and RedBin do not imply current colour. Use task_description for the requested visual identity.'
    request['version'] = 'safe-visual-loop-v2'
    for mode in ('direct', 'diagnostic'):
        bundle[mode+'_messages'] = messages(request, mode=mode)
    return bundle


def build(branch, session, view):
    name = branch.ledger['item']['id']
    case = next(c for c in read(ROOT/'manifest.json')['cases'] if c['item']['id'] == name)
    return decorate(original(branch, session, view), case)


@contextmanager
def context():
    import sv_audit_replay
    with patch.object(sv_requests, 'build', build), patch.object(sv_audit_replay, 'build', build):
        yield
