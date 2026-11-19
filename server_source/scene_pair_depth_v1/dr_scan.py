"""对每个既有实际观测回放门禁，证明未触发的任务保持原行为。"""
from pathlib import Path
import numpy as np
import cv2
from sd_common import read, sha
from reflection.monitors import validate_grounding
from reflection.errors import TaskAbort
from depth_runtime import validator


def scan_step(step):
    assert sha(step['result_path']) == step['result_sha256']
    folder = Path(step['result_path']).parent
    task_folder = folder.parent
    paths = [Path(step['result_path']), folder/'attempt_1'/'depth_evidence.npz',
             folder/'attempt_1'/'plan.json', task_folder/'qualification'/'sensor.npz',
             task_folder/'qualification'/'result.json']
    with np.load(paths[1]) as arrays:
        depth = arrays['noisy'].copy()
    with np.load(paths[3]) as arrays:
        roots = arrays['roots'].copy()
    plan, static = read(paths[2]), read(paths[4])
    events, arrays = [], {}
    validate = validator(validate_grounding, events, arrays)
    names = read(task_folder/'result.json')['item']
    mask_path = folder/'attempt_1'/'mask.png'
    if mask_path.exists():
        actual = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        expected = cv2.erode((roots == static['body_ids'][names['source']]).astype(np.uint8)*255,
                             np.ones((3, 3), np.uint8))
        np.testing.assert_array_equal(expected, actual)
        paths.append(mask_path)
    try:
        validate(plan['action_components'][0]['args']['pixel'], depth, roots, static['body_ids'][names['source']])
        validate(plan['action_components'][2]['args']['pixel'], depth, roots, static['body_ids'][names['destination']])
    except TaskAbort:
        pass
    return dict(index=step['index'], changed=bool(arrays), events=events,
                identities={str(p): sha(p) for p in paths})


def scan(row):
    traces = [scan_step(step) for step in row['new']['steps']]
    return dict(id=row['item']['id'], changed=any(t['changed'] for t in traces), traces=traces)
