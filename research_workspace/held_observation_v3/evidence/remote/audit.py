from unittest.mock import patch
import mujoco
import numpy as np
import spatialmath as sm
from cv_select import scene
from cv_rgb import compare_files
from live_observations import state
from model_grasp_gpu_v1.planning import forbid
from held_observation_v1.common import read,sha
from held_observation_v2.capture import checkpoint
from held_observation_v3.policy import metadata


def compare_view(one,two):
    assert metadata(one)==metadata(two),'Calibration or sensor metadata differs'
    with np.load(one/'sensor.npz') as a,np.load(two/'sensor.npz') as b:
        assert sorted(a.files)==sorted(b.files)
        for key in a.files:
            np.testing.assert_array_equal(a[key],b[key],err_msg=key)
    return compare_files(one/'rgb.png',two/'rgb.png')


def compare_saved(folder,output):
    snapshot=read(folder/'snapshot.json')
    other=read(output/'snapshot.json')
    assert sha(folder/'state.npz')==snapshot['state_sha256']
    assert sha(output/'state.npz')==other['state_sha256']
    assert snapshot==other
    with np.load(folder/'state.npz') as a,np.load(output/'state.npz') as b:
        np.testing.assert_array_equal(a['state'],b['state'])
    current=read(folder/'result.json')
    assert current==read(output/'result.json')
    assert read(folder/'camera_search.json')==read(output/'camera_search.json')
    rgb=[compare_view(folder/f'view_{i}',output/f'view_{i}') for i in range(current['views'])]
    return dict(independently_identical=True,quality_passed=current['quality_passed'],
                views=current['views'],rgb=rgb)


def replay(folder,output):
    snapshot=read(folder/'snapshot.json')
    assert sha(folder/'state.npz')==snapshot['state_sha256']
    with scene(snapshot['case']['config']) as (env,unused):
        with np.load(folder/'state.npz') as data:
            mujoco.mj_setState(env.mj_model,env.mj_data,data['state'],mujoco.mjtState.mjSTATE_INTEGRATION)
        env.robot._base=sm.SE3(np.asarray(snapshot['robot_base']))
        env.robot.robot.base=env.robot._base
        env.robot.set_tool(sm.SE3(np.asarray(snapshot['robot_tool'])))
        mujoco.mj_forward(env.mj_model,env.mj_data)
        before=state(env)
        with patch.object(env,'step',side_effect=forbid):
            checkpoint(env,snapshot['case'],folder=output,phase=snapshot['phase'])
        np.testing.assert_array_equal(before,state(env))
    return compare_saved(folder,output)
