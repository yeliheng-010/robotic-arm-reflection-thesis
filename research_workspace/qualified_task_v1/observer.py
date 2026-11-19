"""返回值只有合格RGB/深度；资格、真值和分割仅存私有诊断。"""
import numpy as np
import mujoco
from grasp_process import camera_calibration_from_env
from sd_inventory import root_boxes
from cv_policy import REQUIRED
from observation_search_v1.record import capture
from surface_grasp_v1.common import save
from qualified_task_v1.snapshot import isolated, rendered


class ObservationRejected(BaseException):
    pass


def calibrated(live, snapshot):
    old_t, old_k = camera_calibration_from_env(live)
    new_t, new_k = camera_calibration_from_env(snapshot)
    np.testing.assert_allclose(old_t.A, new_t.A, atol=1e-10, rtol=0)
    np.testing.assert_allclose(old_k, new_k, atol=1e-10, rtol=0)
    return dict(transform=new_t.A.tolist(), intrinsics=list(new_k))


def observe(env, config, *, folder):
    folder.mkdir(parents=True, exist_ok=False)
    audit = {}
    state = np.empty(mujoco.mj_stateSize(env.mj_model, mujoco.mjtState.mjSTATE_INTEGRATION))
    mujoco.mj_getState(env.mj_model, env.mj_data, state, mujoco.mjtState.mjSTATE_INTEGRATION)
    with (folder/'source_state.npz').open('xb') as stream:
        np.savez_compressed(stream, state=state)
    try:
        with isolated(env, audit) as snapshot, rendered(snapshot) as (resources, samples):
            calibration = calibrated(env, snapshot)
            boxes = root_boxes(snapshot.mj_model, snapshot.mj_data)
            boxes = {name: boxes[name] for name in REQUIRED}
            report, data, rgb = capture(snapshot, resources, camera=config['camera'], boxes=boxes,
                folder=folder, uid=0, diagnostic=False)
            calibrated(env, snapshot)
            save(folder/'qualification.json', report)
            save(folder/'calibration.json', dict(calibration, actual_samples=samples))
            if not report['accepted']:
                raise ObservationRejected('Frozen-camera observation did not qualify')
            result = dict(img=rgb.copy(), depth=data['depth'].copy())
            with (folder/'qualified_sensor.npz').open('xb') as stream:
                np.savez_compressed(stream, **result)
    finally:
        save(folder/'isolation.json', audit)
    return result
