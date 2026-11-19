"""从保存数组重算全部测量与校验，并独立重建状态复算射线。"""
import numpy as np
import mujoco
from types import SimpleNamespace
from cv_metrics import object_metrics
from cv_policy import REQUIRED, frame_gate
from sd_config import MOVING
from sd_scene import compiled
from sf_camera import framed
from depth_diagnostic_v1.numeric import samples, summary
from sensor_independent_v1.reference import ray
from sensor_independent_v1.common import METHODS, read, sha


def calibration(data, *, depth_key, roots_key, reference):
    rows = []
    for name in MOVING:
        rows.extend(samples(data[depth_key], data[roots_key] == reference['body_ids'][name],
            transform=np.asarray(reference['transform']), intrinsics=reference['intrinsics'],
            box=reference['boxes'][name], kernel=3))
    return summary(rows)


def measurements(data, method, *, reference, frame):
    rows = {}
    for name in REQUIRED:
        rows[name] = object_metrics(data[f'{method}_roots'] == reference['body_ids'][name], data[f'{method}_{name}'])
        rows[name]['framed'] = frame['bodies'][name]['passed']
    return rows


def check_rays(env, data, reference):
    for row in reference['rays']:
        actual = ray(env, [row['v'], row['u']], transform=np.asarray(reference['transform']),
                     intrinsics=reference['intrinsics'])
        assert actual == {k: row[k] for k in actual}
        for method in METHODS:
            assert row[method] == dict(depth_m=float(data[f'{method}_depth'][row['v'], row['u']]),
                root=int(data[f'{method}_roots'][row['v'], row['u']]))


def check_pair(folder, env):
    reference = read(folder / 'reference.json')
    assert sha(folder / 'arrays.npz') == reference['arrays_sha256']
    frame = framed(reference['boxes'], reference['row']['camera'])
    assert frame == reference['row']['framing']
    with np.load(folder / 'arrays.npz') as data:
        for method in METHODS:
            recorded = reference['row']['methods'][method]
            rows = measurements(data, method, reference=reference, frame=frame)
            assert rows == recorded['measurements']
            assert frame_gate(rows) == recorded['gate']
            assert calibration(data, depth_key=f'{method}_depth', roots_key=f'{method}_roots',
                               reference=reference) == recorded['calibration']
        assert calibration(data, depth_key='no_msaa_depth', roots_key='original_roots',
                           reference=reference) == reference['row']['fixed_old_mask']
        check_rays(env, data, reference)
    return reference['rays']


def check_layout(folder, config, indices):
    model, data = compiled(config)
    with np.load(folder / 'initial_state.npz') as saved:
        mujoco.mj_setState(model, data, saved['state'], mujoco.mjtState.mjSTATE_INTEGRATION)
    mujoco.mj_forward(model, data)
    env = SimpleNamespace(mj_model=model, mj_data=data)
    return [r for index in indices for r in check_pair(folder / f'pair_{index}', env)]
