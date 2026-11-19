"""记录原始几何候选被过滤的原因；不放宽阈值、不改变候选。"""
import json
import os
from pathlib import Path
import sys

ROOT = Path('/home/yeliheng/grasp_server/overnight_20261019/code')
OUT = Path('/home/yeliheng/grasp_server/diagnosis_20261019')
SOURCES = ('RedBlock', 'GreenCylinder', 'PurpleCapsule', 'OrangeSphere')
SEEDS = (2000, 2001)
VOXEL_SIZE = 0.008
COLLISION_THRESHOLD = 0.01


def detector_values(detector, candidates):
    collision, empty, ious = detector.detect(
        candidates, approach_dist=0.06, collision_thresh=COLLISION_THRESHOLD,
        return_empty_grasp=True, empty_thresh=0.003, return_ious=True)
    return dict(collision=collision.tolist(), empty=empty.tolist(),
                iou_parts=[part.tolist() for part in ious])


def inspect_scene(source, seed, condition):
    import cv2
    import numpy as np
    from reflection.fault_injection import Fault
    from reflection.sim_sensing import SegmentationRenderer
    from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
    from grasp_process import (get_and_process_data, generate_geometric_topdown_grasp,
                               ModelFreeCollisionDetector, camera_calibration_from_env)

    np.random.seed(seed)
    fault = Fault(condition, source, seed, 0.012)
    env = UR5GraspEnv(headless=True, model_editor=fault.model_editor)
    renderer = None
    try:
        env.reset()
        for _ in range(500):
            env.step()
        obs = env.render()
        renderer = SegmentationRenderer(env.mj_model, env.height, env.width)
        roots = renderer.root_map(env.mj_data)
        mask = (roots == env.mj_model.body(source).id).astype(np.uint8) * 255
        mask = cv2.erode(mask, np.ones((3, 3), np.uint8))
        color = cv2.cvtColor(obs['img'], cv2.COLOR_RGB2BGR)
        _, target, scene, _, _ = get_and_process_data(color, obs['depth'], mask, fovy=env.fovy)
        target_points, scene_points = np.asarray(target.points), np.asarray(scene.points)
        candidates = generate_geometric_topdown_grasp(target_points)
        candidates = candidates.nms()
        candidates.sort_by_score()
        transform, _ = camera_calibration_from_env(env)
        return dict(source=source, seed=seed, fault=condition, count=len(candidates),
                    target_points=len(target_points), width=candidates.widths.tolist(),
                    world_approach=(transform.R @ candidates.rotation_matrices[0][:, 0]).tolist(),
                    scene=detector_values(ModelFreeCollisionDetector(scene_points, VOXEL_SIZE), candidates),
                    target_only=detector_values(ModelFreeCollisionDetector(target_points, VOXEL_SIZE), candidates))
    finally:
        if renderer is not None:
            renderer.close()
        env.close()


def main():
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    from reflection.__main__ import bootstrap
    bootstrap()
    records = []
    for source in SOURCES:
        for seed in SEEDS:
            for condition in ('none', 'collision'):
                result = inspect_scene(source, seed, condition)
                records.append(result)
                print(json.dumps(result), flush=True)
    (OUT / 'geometry_result.json').write_text(json.dumps(records, indent=2))


if __name__ == '__main__':
    main()

