"""训练场景的原/新候选分部占据诊断，不执行机器人动作。"""
import json
from pathlib import Path
import cv2
import numpy as np
from reflection.fault_injection import Fault
from reflection.sim_sensing import SegmentationRenderer
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from grasp_process import (get_and_process_data, ModelFreeCollisionDetector,
                           camera_calibration_from_env, rank_grasp_candidates)
from geometry.candidates import generate

OUT = Path('/home/yeliheng/grasp_server/geometry_20261019')
SOURCES = ('RedBlock', 'GreenCylinder', 'PurpleCapsule', 'OrangeSphere')
SEED = 2000
VOXEL = .008


def finger_masks(detector, grasp):
    points = (detector.scene_points - grasp.translation) @ grasp.rotation_matrix
    x, y, z = points.T
    height = np.abs(z) < grasp.height / 2
    length = (x > grasp.depth - detector.finger_length) & (x < grasp.depth)
    left = (y > -grasp.width/2-detector.finger_width) & (y < -grasp.width/2)
    right = (y < grasp.width/2+detector.finger_width) & (y > grasp.width/2)
    return {'left': height & length & left, 'right': height & length & right}


def occupied_points(detector, grasp, *, env, roots):
    transform, intrinsics = camera_calibration_from_env(env)
    fx, fy, cx, cy = intrinsics
    parts = {}
    for name, mask in finger_masks(detector, grasp).items():
        points = detector.scene_points[mask]
        world = points @ transform.R.T + transform.t
        u = np.clip(np.rint(fx*points[:, 0]/points[:, 2]+cx).astype(int), 0, roots.shape[1]-1)
        v = np.clip(np.rint(fy*points[:, 1]/points[:, 2]+cy).astype(int), 0, roots.shape[0]-1)
        labels = [env.mj_model.body(int(i)).name for i in roots[v, u]]
        parts[name] = {'count': len(points), 'world_xyz': world.tolist(),
                       'projected_root_labels': labels}
    return parts


def inspect(source, condition):
    np.random.seed(SEED)
    fault = Fault(condition, source, SEED, .012)
    env = UR5GraspEnv(headless=True, model_editor=fault.model_editor)
    renderer = None
    try:
        env.reset()
        for _ in range(500):
            env.step()
        obs = env.render()
        renderer = SegmentationRenderer(env.mj_model, env.height, env.width)
        roots = renderer.root_map(env.mj_data)
        mask = (roots == env.mj_model.body(source).id).astype(np.uint8)*255
        mask = cv2.erode(mask, np.ones((3, 3), np.uint8))
        color = cv2.cvtColor(obs['img'], cv2.COLOR_RGB2BGR)
        _, target, scene, mask, depth = get_and_process_data(color, obs['depth'], mask, fovy=env.fovy)
        points, scene_points = np.asarray(target.points), np.asarray(scene.points)
        np.savez_compressed(OUT / f'{source}-{condition}.npz', target=points, scene=scene_points)
        group = generate(points)
        detector = ModelFreeCollisionDetector(scene_points, voxel_size=VOXEL)
        collision, empty, ious = detector.detect(group, approach_dist=.06, collision_thresh=.01,
            return_empty_grasp=True, empty_thresh=.003, return_ious=True)
        candidates = group.nms()
        candidates.sort_by_score()
        c, e = detector.detect(candidates, approach_dist=.06, collision_thresh=.01,
                               return_empty_grasp=True, empty_thresh=.003)
        survivors = candidates[~(c | e)]
        ranked = rank_grasp_candidates(survivors, points, mask, depth, fovy=env.fovy) if len(survivors) else []
        return {'source': source, 'fault': condition, 'seed': SEED,
                'raw': len(group), 'nms': len(candidates), 'ranked': len(ranked),
                'widths': group.widths.tolist(), 'collision': collision.tolist(), 'empty': empty.tolist(),
                'ious': [x.tolist() for x in ious],
                'original_occupancy': occupied_points(detector, group[0], env=env, roots=roots)}
    finally:
        if renderer is not None:
            renderer.close()
        env.close()


def main():
    rows = []
    for source in SOURCES:
        for fault in ('none', 'collision'):
            row = inspect(source, fault)
            rows.append(row)
            print(json.dumps(row), flush=True)
    (OUT / 'probe.json').write_text(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()

