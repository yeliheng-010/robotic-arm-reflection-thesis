import sys
from unittest.mock import patch
import mujoco
import numpy as np
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
from cv_select import scene
from cv_rgb import compare_files
from live_observations import state
from model_grasp_gpu_v1.planning import forbid
from held_observation_v1.common import TRIAL,PROJECT,read,save,sha,registered
from held_observation_v1.capture import checkpoint


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
            current=checkpoint(env,snapshot['case'],folder=output,phase=snapshot['phase'])
        np.testing.assert_array_equal(before,state(env))
    assert current==read(folder/'result.json')
    assert read(output/'snapshot.json')['tcp_encoder_pose']==snapshot['tcp_encoder_pose']
    assert read(output/'camera_search.json')==read(folder/'camera_search.json')
    for index in range(current['views']):
        a,b=folder/f'view_{index}',output/f'view_{index}'
        assert read(a/'calibration.json')==read(b/'calibration.json')
        compare_files(a/'rgb.png',b/'rgb.png')
    return dict(independently_identical=True,quality_passed=current['quality_passed'],views=current['views'])


def preflight():
    registered()
    result=replay(TRIAL/'preflight/checkpoints/preflight',TRIAL/'replay/preflight')
    save(TRIAL/'preflight_audit.json',dict(passed=result['quality_passed'],independent=True,
        audit_verified=True,physical_attempts=0,observation=result))


def physical_trace(folder):
    import json
    old=PROJECT/'surface_physical_v1/trial/cases/964347/first'
    actual=[json.loads(s) for s in (folder/'contacts.jsonl').read_text().splitlines()]
    previous=[json.loads(s) for s in (old/'contacts.jsonl').read_text().splitlines()]
    expected=[r for r in previous if r['action'] in ('move_to_grasp_pose','close_gripper','move_to_point')]
    assert actual==expected,'Observation changed recorded physical trace before release'
    planners=read(folder/'bridge.json')['planners']
    old_plans=read(old/'bridge.json')['planners'][:len(planners)]
    assert planners==old_plans
    assert not read(folder/'guard.json')['open_called']
    life=read(folder/'lifecycle.json')
    assert life['released'] and life['actual_close_calls']==1 and life['close_error'] is None
    return dict(contact_rows=len(actual),trajectory_identical_to_original_before_release=True,lifecycle=life)


def physical():
    registered()
    folder=TRIAL/'cases/964347/first'
    result=read(TRIAL/'outcome.json')
    assert result['stopped_before_release'] and result['physical_attempts']==1
    checked={phase:replay(folder/'checkpoints'/phase,TRIAL/'replay'/phase)
             for phase in ('after_lift','before_release')}
    trace=physical_trace(folder)
    paths=[p for p in (TRIAL/'cases').rglob('*') if p.is_file()]
    save(TRIAL/'audit.json',dict(passed=True,phases=checked,trace=trace,
        physical_attempts=1,release_executed=False,task_success=None,model_calls=0,training_eligible=False,
        identities={str(p):sha(p) for p in paths}))
    print(dict(audited=True,phases=checked,release_executed=False),flush=True)


if __name__=='__main__':
    {'preflight':preflight,'physical':physical}[sys.argv[1]]()
