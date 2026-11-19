"""保存预定配对数组与私有射线证据；参考值不参与相机选择。"""
import cv2
import mujoco
import numpy as np
from sd_config import MOVING
from grasp_process import camera_calibration_from_env
from sensor_independent_v1.common import METHODS, save, sha


def reference_pixels(roots, bid):
    interior = cv2.erode((roots == bid).astype(np.uint8), np.ones((3, 3), np.uint8))
    pixels = np.argwhere(interior)
    pixels = pixels[::max(1, len(pixels)//64)]
    return [pixels[i] for i in sorted({0, len(pixels)//2, len(pixels)-1})] if len(pixels) else []


def ray(env, pixel, *, transform, intrinsics):
    v, u = [int(value) for value in pixel]
    fx, fy, cx, cy = intrinsics
    vector = np.array([(u+.5-cx)/fx, (v+.5-cy)/fy, 1.])
    norm = np.linalg.norm(vector)
    gid = np.array([-1], dtype=np.int32)
    distance = mujoco.mj_ray(env.mj_model, env.mj_data, transform[:3, 3],
        transform[:3, :3] @ (vector/norm), np.array([1, 1, 1, 0, 0, 0], dtype=np.uint8), 1, -1, gid)
    root = int(env.mj_model.body_rootid[env.mj_model.geom_bodyid[gid[0]]]) if gid[0] >= 0 else -1
    return dict(u=u, v=v, ray_geom=int(gid[0]), ray_root=root,
                ray_depth_m=float(distance/norm) if distance >= 0 else None)


def rays(env, data, *, transform, intrinsics):
    rows = []
    for name in MOVING:
        bid = env.mj_model.body(name).id
        for pixel in reference_pixels(data['original']['roots'], bid):
            row = ray(env, pixel, transform=transform, intrinsics=intrinsics)
            row['reference_object'] = name
            for method in METHODS:
                row[method] = dict(depth_m=float(data[method]['depth'][pixel[0], pixel[1]]),
                    root=int(data[method]['roots'][pixel[0], pixel[1]]))
            rows.append(row)
    return rows


def save_pair(env, data, *, folder, row, boxes):
    folder.mkdir(exist_ok=False)
    arrays = {}
    for method, values in data.items():
        arrays.update({f'{method}_depth': values['depth'], f'{method}_roots': values['roots']})
        arrays.update({f'{method}_{name}': outline for name, outline in values['outlines'].items()})
    with (folder / 'arrays.npz').open('xb') as stream:
        np.savez_compressed(stream, **arrays)
    transform, intrinsics = camera_calibration_from_env(env)
    save(folder / 'reference.json', dict(row=row, boxes=boxes, transform=transform.A.tolist(),
        intrinsics=list(intrinsics), arrays_sha256=sha(folder / 'arrays.npz'),
        body_ids={name: int(env.mj_model.body(name).id) for name in values['outlines']},
        rays=rays(env, data, transform=transform.A, intrinsics=intrinsics), private_only=True))
