from contextlib import contextmanager
from unittest.mock import patch
import mujoco
import numpy as np
from cv_policy import REQUIRED
from sd_inventory import root_boxes
from reflection.sim_sensing import SegmentationRenderer
from live_observations import state
from model_grasp_gpu_v1.planning import forbid
from held_observation_v1.common import save,sha
from held_observation_v1.views import search
from held_observation_v1.geometry import estimate


@contextmanager
def camera_restored(env):
    model=env.mj_model
    index=model.camera('cam').id
    original=[model.cam_pos[index].copy(),model.cam_quat[index].copy(),float(model.cam_fovy[index]),env.fovy]
    try:
        yield
    finally:
        model.cam_pos[index],model.cam_quat[index],model.cam_fovy[index],env.fovy=original
        mujoco.mj_forward(model,env.mj_data)


def encoder_tcp(env):
    q=np.array([float(env.mj_data.joint(name).qpos[0]) for name in env.joint_names])
    return env.robot.fkine(q).A


def private_truth(env,case,result):
    center=env.mj_data.body(case['item']['source']).xpos.copy()
    values=dict(source_center_world_m=center.tolist(),private_simulation_truth=True)
    if result['quality_passed']:
        values['estimated_center_error_m']=float(np.linalg.norm(center-result['center_world_m']))
    return values


def checkpoint(env,case,*,folder,phase):
    folder.mkdir(parents=True,exist_ok=False)
    before=state(env)
    with (folder/'state.npz').open('xb') as stream:
        np.savez_compressed(stream,state=before)
    tcp=encoder_tcp(env)
    save(folder/'snapshot.json',dict(phase=phase,time_s=float(env.mj_data.time),
        state_sha256=sha(folder/'state.npz'),case=case,tcp_encoder_pose=tcp.tolist(),
        robot_base=env.robot._base.A.tolist(),robot_tool=env.robot._tool.A.tolist()))
    renderer=SegmentationRenderer(env.mj_model,env.height,env.width)
    try:
        with camera_restored(env),patch.object(env,'step',side_effect=forbid), \
             patch.object(mujoco,'mj_step',forbid),patch.object(mujoco,'mj_step1',forbid), \
             patch.object(mujoco,'mj_step2',forbid):
            all_boxes=root_boxes(env.mj_model,env.mj_data)
            boxes={name:all_boxes[name] for name in REQUIRED}
            clouds=search(env,renderer,case,folder=folder,phase=phase,boxes=boxes)
            result=estimate(clouds,tcp)
    finally:
        renderer.close()
        np.testing.assert_array_equal(before,state(env))
    save(folder/'private_truth.json',private_truth(env,case,result))
    result.update(state_unchanged=True,views=len(clouds),phase=phase,model_calls=0,training_eligible=False)
    save(folder/'result.json',result)
    if result['quality_passed']:
        public={k:v for k,v in result.items() if k!='quality'}
        save(folder/'public.json',public)
    print(dict(phase=phase,views=len(clouds),quality_passed=result['quality_passed']),flush=True)
    return result
