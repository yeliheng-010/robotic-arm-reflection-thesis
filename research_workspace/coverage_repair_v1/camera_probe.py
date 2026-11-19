import sys
from pathlib import Path
from unittest.mock import patch
import mujoco
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from cv_select import scene, evaluate, image
from cv_policy import REQUIRED
from cv_rgb import compare_files
from sd_inventory import root_boxes
from live_observations import state
from camera_search import rank, occluders, search
from common import ROOT, read, save, sha, verify


def restore(env, spec):
    if 'selection' in spec:
        previous = read(spec['selection'])['attempts']
        return previous[0], [r['camera'] for r in rank(previous)], [r['camera'] for r in previous]
    report = read(spec['snapshot'])
    assert sha(report['state_path'])==report['state_sha256']
    with np.load(report['state_path']) as snapshot:
        mujoco.mj_setState(env.mj_model,env.mj_data,snapshot['state'],mujoco.mjtState.mjSTATE_INTEGRATION)
    mujoco.mj_forward(env.mj_model,env.mj_data)
    return report,[spec['config']['camera']],[spec['config']['camera']]


def run(spec, mode):
    folder = ROOT/mode/spec['name']
    folder.mkdir(parents=True,exist_ok=False)
    with scene(spec['config']) as (env,renderer):
        expected,anchors,previous = restore(env,spec)
        before = state(env)
        boxes = root_boxes(env.mj_model,env.mj_data)
        boxes = {name:boxes[name] for name in REQUIRED}
        with patch.object(env,'step',side_effect=AssertionError('Motion forbidden during snapshot search')):
            original = evaluate(env,renderer,spec['config']['camera'],boxes=boxes)
            assert original['measurements']==expected['measurements']
            private = occluders(env,renderer,original)
            image(env,folder/'before.png')
            result = search(env,renderer,spec,boxes=boxes,folder=folder,anchors=anchors,previous=previous)
        np.testing.assert_array_equal(before,state(env))
    result.update(original=original,occlusion_audit=private)
    if mode=='audit':
        assert result==read(ROOT/'probe'/spec['name']/'result.json')
        if result['accepted']:
            compare_files(ROOT/'probe'/spec['name']/'after.png',folder/'after.png')
    save(folder/'result.json',result)
    print(dict(name=spec['name'],mode=mode,accepted=result['accepted'],checked=result['checked']),flush=True)


if __name__=='__main__':
    for spec in verify(ROOT/'manifest.json')['rows']:
        run(spec,sys.argv[1])
