"""不读取对象真值；从同一实际含噪深度得到可见邻域。"""
import numpy as np
from model_grasp_intent_v1.observations import validate

NEIGHBOUR_RADIUS_M = .30
MAX_SCENE_POINTS = 100000


def prepare(arrays, calibration, nominal):
    points = np.asarray(arrays['world_points'], dtype=float)
    camera = np.asarray(arrays['camera_points'], dtype=float)
    matrix = np.asarray(calibration['transform'], dtype=float)
    if not np.array_equal(camera@matrix[:3,:3].T+matrix[:3,3], points):
        raise ValueError('Frozen camera/world projection mismatch')
    depth, mask = arrays['depth'], arrays['mask'].astype(bool)
    valid = np.isfinite(depth) & (depth > 0) & ~mask
    v, u = np.where(valid)
    fx, fy, cx, cy = calibration['intrinsics']
    z = depth[v,u]
    scene = np.column_stack(((u-cx)*z/fx, (v-cy)*z/fy, z))@matrix[:3,:3].T+matrix[:3,3]
    scene = scene[np.linalg.norm(scene-np.median(points,axis=0),axis=1) <= NEIGHBOUR_RADIUS_M]
    if len(scene) > MAX_SCENE_POINTS:
        indices = np.linspace(0,len(scene)-1,MAX_SCENE_POINTS,dtype=int)
        scene = scene[indices]
    return validate(dict(qualified=True, revision=0, target_points=points.tolist(),
                         scene_points=scene.tolist(), nominal=list(nominal)))
