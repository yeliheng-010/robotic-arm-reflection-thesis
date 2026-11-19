from contextlib import contextmanager
from unittest.mock import patch
import mujoco
import numpy as np
import spatialmath as sm
from cv_select import scene
from cv_metrics import measure,isolated_mask
from cv_policy import REQUIRED
from sf_select import set_camera,verify_projection
from sf_camera import framed
from sd_inventory import root_boxes
from sd_render import depth_check
from sd_runtime import render
from live_observations import state
from grasp_process import camera_calibration_from_env
from diversity.noise import corrupt_depth
from model_grasp_gpu_v1.planning import forbid
from held_observation_v1.views import points
from surface_grasp_v1.common import read,save,sha
from visibility_calibration_v1.policy import NOISE_REPEATS

SEED_PREFIX=976511


@contextmanager
def restored(folder):
    snapshot=read(folder/'snapshot.json')
    assert sha(folder/'state.npz')==snapshot['state_sha256']
    with scene(snapshot['case']['config']) as (env,renderer):
        with np.load(folder/'state.npz') as data:
            mujoco.mj_setState(env.mj_model,env.mj_data,data['state'],mujoco.mjtState.mjSTATE_INTEGRATION)
        env.robot._base=sm.SE3(np.asarray(snapshot['robot_base']))
        env.robot.robot.base=env.robot._base
        env.robot.set_tool(sm.SE3(np.asarray(snapshot['robot_tool'])))
        mujoco.mj_forward(env.mj_model,env.mj_data)
        initial=state(env)
        with patch.object(env,'step',side_effect=forbid),patch.object(mujoco,'mj_step',forbid), \
             patch.object(mujoco,'mj_step1',forbid),patch.object(mujoco,'mj_step2',forbid):
            yield env,renderer,snapshot
            np.testing.assert_array_equal(initial,state(env))


def noisy_clouds(env,raw,*,mask,snapshot,phase_id,index):
    transform,intrinsics=camera_calibration_from_env(env)
    clouds,stats=[],[]
    for repeat in range(NOISE_REPEATS):
        seed=[SEED_PREFIX,snapshot['case']['item']['seed'],phase_id,index,repeat]
        depth,noise=corrupt_depth(raw,snapshot['case']['config']['sensor'],seed=np.random.SeedSequence(seed))
        clouds.append(points(depth,mask,transform=transform.A,intrinsics=intrinsics))
        stats.append(dict(seed=seed,noise=noise,points=len(clouds[-1])))
    return clouds,dict(transform=transform.A.tolist(),intrinsics=list(intrinsics),samples=stats)


def view(env,renderer,*,camera,boxes,snapshot,phase_id,index,folder):
    frame=framed(boxes,camera)
    base=dict(index=index,camera=camera,source_fraction=0.,source_pixels=0)
    if not frame['passed']:
        return dict(base,report=dict(reason='framing_rejected'),calibration_passed=False),None
    set_camera(env,camera)
    verify_projection(env,camera,boxes)
    report,roots=measure(env,renderer,frame)
    report['framing']=frame
    raw=render(env)
    calibration=depth_check(env,raw['depth'],roots)
    name=snapshot['case']['item']['source']
    metrics=report['measurements'][name]
    row=dict(base,report=report,calibration=calibration,calibration_passed=bool(calibration['passed']),
             source_fraction=report['gate']['objects'][name]['visible_fraction'],source_pixels=metrics['pixels'])
    if not calibration['passed']:
        return row,None
    mask=(roots==env.mj_model.body(name).id)&isolated_mask(env,renderer,name)
    clouds,metadata=noisy_clouds(env,raw['depth'],mask=mask,snapshot=snapshot,phase_id=phase_id,index=index)
    folder.mkdir(parents=True,exist_ok=False)
    with (folder/'clouds.npz').open('xb') as stream:
        np.savez_compressed(stream,**{f'noise_{i}':cloud for i,cloud in enumerate(clouds)})
    save(folder/'metadata.json',dict(metadata,clouds_sha256=sha(folder/'clouds.npz')))
    return row,clouds


def capture(source,output,*,phase_id):
    output.mkdir(parents=True,exist_ok=False)
    cameras=read(source/'camera_search.json')['attempts']
    rows,clouds=[],{}
    with restored(source) as (env,renderer,snapshot):
        all_boxes=root_boxes(env.mj_model,env.mj_data)
        boxes={name:all_boxes[name] for name in REQUIRED}
        geom=env.mj_model.geom('purple_capsule').id
        assert int(env.mj_model.geom_type[geom])==int(mujoco.mjtGeom.mjGEOM_CAPSULE)
        truth=dict(center=env.mj_data.geom_xpos[geom].tolist(),
            axis=env.mj_data.geom_xmat[geom].reshape(3,3)[:,2].tolist(),private_simulation_truth=True)
        for attempt in cameras:
            index=attempt['index']
            row,data=view(env,renderer,camera=attempt['camera'],boxes=boxes,snapshot=snapshot,
                phase_id=phase_id,index=index,folder=output/f'view_{index}')
            rows.append(row)
            if data is not None:
                clouds[index]=data
    save(output/'views.json',rows)
    save(output/'private_truth.json',truth)
    save(output/'state_check.json',dict(integration_state_unchanged=True,isolated_environment=True,
        source_state_sha256=sha(source/'state.npz'),task_motion_steps=0))
    return rows,clouds
