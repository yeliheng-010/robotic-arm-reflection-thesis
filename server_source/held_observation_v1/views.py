import cv2
import numpy as np
from cv_select import evaluate
from sf_camera import proposal,framed
from live_observations import masks
from sd_runtime import render
from grasp_process import camera_calibration_from_env
from diversity.noise import corrupt_depth
from coverage_repair_v1.proposals import cameras
from held_observation_v1.common import save,sha,PHASES,CAMERA_BUDGET,MIN_VIEW_ANGLE_DEG


def points(depth,mask,*,transform,intrinsics):
    v,u=np.where(mask & np.isfinite(depth) & (depth>0))
    z=depth[v,u]
    fx,fy,cx,cy=intrinsics
    camera=np.column_stack(((u-cx)*z/fx,(v-cy)*z/fy,z))
    return camera@transform[:3,:3].T+transform[:3,3]


def separated(camera,previous):
    if not previous:
        return True
    a=np.asarray(camera['position'])-camera['target'];a/=np.linalg.norm(a)
    b=np.asarray(previous[0]['position'])-previous[0]['target'];b/=np.linalg.norm(b)
    return np.rad2deg(np.arccos(np.clip(np.dot(a,b),-1.,1.)))>=MIN_VIEW_ANGLE_DEG


def proposals(config,boxes):
    original=config['camera']
    local=cameras([original],boxes,previous=[original])[:12]
    other=[proposal(config['seed'],index,boxes=boxes) for index in range(1,CAMERA_BUDGET)]
    return ([original]+local+other)[:CAMERA_BUDGET]


def acquire(env,case,*,folder,phase,index,camera):
    folder.mkdir(parents=True,exist_ok=False)
    raw=render(env)
    seed=[976401,case['item']['seed'],PHASES[phase],index]
    noisy,stats=corrupt_depth(raw['depth'],case['config']['sensor'],seed=np.random.SeedSequence(seed))
    segmentation=masks(env,case['item'])
    transform,intrinsics=camera_calibration_from_env(env)
    world=points(noisy,segmentation['source'],transform=transform.A,intrinsics=intrinsics)
    with (folder/'sensor.npz').open('xb') as stream:
        np.savez_compressed(stream,clean=raw['depth'],noisy=noisy,source_mask=segmentation['source'],
            destination_mask=segmentation['destination'],world_points=world)
    assert cv2.imwrite(str(folder/'rgb.png'),cv2.cvtColor(raw['img'],cv2.COLOR_RGB2BGR))
    save(folder/'calibration.json',dict(transform=transform.A.tolist(),intrinsics=list(intrinsics),
        camera=camera,seed_components=seed,noise=stats,point_count=len(world),
        segmentation_source='simulation_assisted',position_source='noisy_depth_backprojection',
        sensor_sha256=sha(folder/'sensor.npz'),rgb_sha256=sha(folder/'rgb.png')))
    return world


def search(env,renderer,case,*,folder,phase,boxes):
    attempts,accepted,clouds=[],[],[]
    for index,camera in enumerate(proposals(case['config'],boxes)):
        if not framed(boxes,camera)['passed']:
            report=dict(accepted=False,reason='framing_rejected')
        else:
            report=evaluate(env,renderer,camera,boxes=boxes)
        attempts.append(dict(index=index,camera=camera,report=report))
        if report['accepted'] and separated(camera,accepted):
            clouds.append(acquire(env,case,folder=folder/f'view_{len(accepted)}',
                phase=phase,index=index,camera=camera))
            accepted.append(camera)
        if len(accepted)==2:
            break
    save(folder/'camera_search.json',dict(attempts=attempts,accepted=accepted,
        maximum=CAMERA_BUDGET,checked=len(attempts),minimum_angle_deg=MIN_VIEW_ANGLE_DEG))
    return clouds
