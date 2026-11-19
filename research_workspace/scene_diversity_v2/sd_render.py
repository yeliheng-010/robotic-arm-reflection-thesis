"""真实 RGB/深度/分割一致性与可见性资格检查。"""
import os
from pathlib import Path
import cv2
import mujoco
import numpy as np
from sd_config import ROOT, SEEDS, GROUPS, MOVING
from sd_common import save, verify, sha
from sd_runtime import context
from sd_scene import apply
from sd_inventory import root_boxes
from reflection.sim_sensing import SegmentationRenderer
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from grasp_process import camera_calibration_from_env

PIXEL_MINIMUM = 64
VISIBILITY_MINIMUM = .70
DEPTH_TOLERANCE = .006
EDGE_KERNEL = np.ones((3, 3), dtype=np.uint8)


def isolated_count(env, renderer, name):
    model = env.mj_model
    old = model.geom_group.copy()
    mask = model.body_rootid[model.geom_bodyid] == model.body(name).id
    options = mujoco.MjvOption()
    options.geomgroup[:] = 0
    options.geomgroup[5] = 1
    try:
        model.geom_group[:] = 0
        model.geom_group[mask] = 5
        renderer.renderer.update_scene(env.mj_data, 'cam', scene_option=options)
        segmentation = renderer.renderer.render()
        return int(np.count_nonzero(segmentation[..., 0] >= 0))
    finally:
        model.geom_group[:] = old


def depth_check(env, depth, roots):
    transform, intrinsics = camera_calibration_from_env(env)
    fx, fy, cx, cy = intrinsics
    boxes = root_boxes(env.mj_model, env.mj_data)
    errors = []
    for name in MOVING:
        mask = (roots == env.mj_model.body(name).id).astype(np.uint8)
        interior = cv2.erode(mask, EDGE_KERNEL)
        pixels = np.argwhere(interior)
        if len(pixels) == 0:
            continue
        pixels = pixels[::max(1, len(pixels)//64)]
        v, u = pixels.T
        z = depth[v, u]
        points = np.column_stack(((u-cx)*z/fx, (v-cy)*z/fy, z))
        world = points@transform.R.T + transform.t
        box = np.array(boxes[name])
        errors.extend(np.max(np.maximum(box[0]-world, world-box[1]), axis=1).tolist())
    maximum = max([0.]+errors)
    return dict(passed=bool(errors) and maximum <= DEPTH_TOLERANCE,
                samples=len(errors), max_outside_bounds_m=maximum, edge_kernel_pixels=3)


def visibility(env, roots, renderer):
    result = {}
    for name in MOVING:
        visible = int(np.count_nonzero(roots == env.mj_model.body(name).id))
        isolated = isolated_count(env, renderer, name)
        ratio = visible/max(1, isolated)
        result[name] = dict(pixels=visible, isolated_pixels=isolated, visible_fraction=ratio,
                            qualified=visible >= PIXEL_MINIMUM and ratio >= VISIBILITY_MINIMUM)
    return result


def capture(env, folder):
    observation = env.render()
    rgb_path = folder/'rgb.png'
    assert cv2.imwrite(str(rgb_path), cv2.cvtColor(observation['img'], cv2.COLOR_RGB2BGR))
    renderer = SegmentationRenderer(env.mj_model, env.height, env.width)
    try:
        roots = renderer.root_map(env.mj_data)
        seen = visibility(env, roots, renderer)
        depth = depth_check(env, observation['depth'], roots)
        np.savez_compressed(folder/'sensor.npz', depth=observation['depth'], roots=roots)
    finally:
        renderer.close()
    transform, intrinsics = camera_calibration_from_env(env)
    return dict(visibility=seen, calibration=depth, camera_transform=transform.A.tolist(),
                intrinsics=list(intrinsics), fovy_rad=float(env.fovy), rgb_sha256=sha(rgb_path),
                sensor_sha256=sha(folder/'sensor.npz'),
                body_ids={name: int(env.mj_model.body(name).id) for name in MOVING},
                body_positions={name: env.mj_data.body(name).xpos.tolist() for name in MOVING})


def probe(config, folder):
    folder.mkdir(parents=True, exist_ok=False)
    with context(config):
        env = UR5GraspEnv(headless=True, model_editor=lambda spec: apply(spec, config))
        try:
            env.reset()
            for _ in range(500):
                env.step()
            result = capture(env, folder)
        finally:
            env.close()
    result.update(seed=config['seed'], group=config['group'],
                  geometry_accepted=config['geometry_accepted'], compiled_check=config['compiled_check'])
    save(folder/'result.json', result)
    return result


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = verify()
    rows = []
    for seed in SEEDS[:6]:
        for group in GROUPS:
            key = str(seed)+'_'+group
            row = probe(manifest['configs'][key], ROOT/'renders'/key)
            rows.append(row)
            print(key, row['calibration'], flush=True)
    save(ROOT/'render_verification.json', dict(complete=True, accounted=len(rows), rows=rows,
         passed=all(r['calibration']['passed'] for r in rows), manifest_sha256=sha(ROOT/'manifest.json')))


if __name__ == '__main__':
    main()
