"""暂停状态上的真实RGB-D采集；噪声审计和干净深度留在私有侧。"""
import cv2
import mujoco
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from sd_runtime import render
from sd_common import save, sha
from diversity.noise import corrupt_depth
from diversity.runtime import digest
from reflection.sim_sensing import SegmentationRenderer
from grasp_process import camera_calibration_from_env
from live_budget import ObservationBudget
from sensor_math import surface

NAMESPACE = 963800


def state(env):
    spec = mujoco.mjtState.mjSTATE_INTEGRATION
    values = np.empty(mujoco.mj_stateSize(env.mj_model, spec))
    mujoco.mj_getState(env.mj_model, env.mj_data, values, spec)
    return values


def masks(env, item):
    renderer = SegmentationRenderer(env.mj_model, env.height, env.width)
    try:
        roots = renderer.root_map(env.mj_data)
        return {key: cv2.erode((roots == env.mj_model.body(item[key]).id).astype(np.uint8),
                               np.ones((3, 3), dtype=np.uint8)).astype(bool)
                for key in ('source', 'destination')}
    finally:
        renderer.close()


class Sampler:
    def __init__(self, env, config, *, item, folder, attempt, success):
        self.env, self.config, self.item, self.folder = env, config, item, folder
        self.attempt = attempt
        self.budget = ObservationBudget(attempt=attempt, success=success)
        self.rows, self.private = [], []

    def capture(self):
        number = self.budget.reserve()
        folder = self.folder/f'observation_{number}'
        folder.mkdir(parents=True, exist_ok=False)
        before = state(self.env)
        raw = render(self.env)
        seed = [NAMESPACE, self.config['seed'], self.attempt, number]
        noisy, stats = corrupt_depth(raw['depth'], self.config['sensor'], seed=np.random.SeedSequence(seed))
        segmentation = masks(self.env, self.item)
        transform, intrinsics = camera_calibration_from_env(self.env)
        observed = {key: surface(noisy, mask, transform=transform.A, intrinsics=intrinsics)
                    for key, mask in segmentation.items()}
        after = state(self.env)
        np.testing.assert_array_equal(before, after)
        row = dict(observation_index=number, attempt=self.attempt, time_s=float(self.env.mj_data.time),
                   observed=observed, acquisition='fresh_rgbd_render_paused_state',
                   perception='simulation_assisted_segmentation_noisy_depth_surface_statistics')
        audit = self.store(folder, raw, noisy=noisy, segmentation=segmentation,
                           stats=stats, seed=seed, frozen=before, calibration=(transform.A, intrinsics))
        save(folder/'public.json', row)
        self.rows.append(row)
        self.private.append(audit)
        return row

    def store(self, folder, raw, *, noisy, segmentation, stats, seed, frozen, calibration):
        assert cv2.imwrite(str(folder/'rgb.png'), cv2.cvtColor(raw['img'], cv2.COLOR_RGB2BGR))
        np.savez_compressed(folder/'private_sensor.npz', clean=raw['depth'], noisy=noisy,
                            source_mask=segmentation['source'], destination_mask=segmentation['destination'])
        transform, intrinsics = calibration
        audit = dict(stats=stats, seed_components=seed, state_unchanged=True,
                     state_sha256=digest(frozen), clean_sha256=digest(raw['depth']), noisy_sha256=digest(noisy),
                     rgb_sha256=sha(folder/'rgb.png'), sensor_sha256=sha(folder/'private_sensor.npz'),
                     transform=transform.tolist(), intrinsics=list(intrinsics))
        save(folder/'audit.json', audit)
        return audit
