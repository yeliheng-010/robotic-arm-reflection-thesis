from pathlib import Path
import traceback
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import mujoco
from cv_select import scene
from cv_rgb import compare
from sf_camera import framed
from sf_select import set_camera
from camera_joint_v1.search import global_camera
from pose_fresh_v1.observe import paused
from sensor_independent_v1 import sensor
from sensor_independent_v1.common import verify as verify_source
from surface_grasp_v1.common import read, save, sha

ROOT = Path(__file__).resolve().parent
RUN = ROOT / 'run'
SOURCE = ROOT.parent / 'sensor_independent_v1/run'
SEEDS = (978301, 978302)


def frames(env, segment, *, camera, boxes):
    set_camera(env, camera)
    frame = framed(boxes, camera)
    values = dict(initial=sensor.rgb(env), repeat=sensor.rgb(env))
    sensor.capture(env, (env.mj_depth_renderer, segment), frame)
    values['original_geometry'] = sensor.rgb(env)
    with sensor.paired(env, segment) as (resources, actual):
        sensor.capture(env, resources['no_msaa'], frame)
        values['no_msaa_geometry'] = sensor.rgb(env)
        sensor.capture(env, resources['original'], frame)
        sensor.capture(env, resources['no_msaa'], frame)
        values['both_geometry'] = sensor.rgb(env)
    return values, actual


def comparisons(values):
    names = list(values)
    return dict(relative_to_first={name: compare(values[names[0]], value) for name, value in values.items()},
        adjacent={name: compare(values[previous], values[name]) for previous, name in zip(names, names[1:])})


def run_case(seed, config):
    folder = RUN / str(seed)
    folder.mkdir(exist_ok=False)
    boxes = read(SOURCE / str(seed) / 'boxes.json')
    cameras = ((i, global_camera(config, boxes, i)) for i in range(128))
    index, camera = next((i, c) for i, c in cameras if framed(boxes, c)['passed'])
    with scene(config) as (env, segment):
        with np.load(SOURCE / str(seed) / 'initial_state.npz') as data:
            mujoco.mj_setState(env.mj_model, env.mj_data, data['state'], mujoco.mjtState.mjSTATE_INTEGRATION)
        mujoco.mj_forward(env.mj_model, env.mj_data)
        with paused(env, folder):
            values, actual = frames(env, segment, camera=camera, boxes=boxes)
    np.savez_compressed(folder / 'rgb.npz', **values)
    result = dict(seed=seed, index=index, camera=camera, actual_samples=actual,
                  comparisons=comparisons(values), arrays_sha256=sha(folder / 'rgb.npz'))
    save(folder / 'result.json', result)
    return result


def main():
    manifest = verify_source()
    RUN.mkdir(exist_ok=False)
    inputs = {str(SOURCE / str(seed) / name): sha(SOURCE / str(seed) / name)
              for seed in SEEDS for name in ('initial_state.npz', 'boxes.json', 'failure.json')}
    identities = dict(manifest['identities'])
    identities.update({str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.md', '.sbatch')})
    save(RUN / 'started.json', dict(inputs=inputs, identities=identities))
    try:
        result = {str(s): run_case(s, manifest['configs'][str(s)]) for s in SEEDS}
        assert all(sha(p) == digest for p, digest in inputs.items())
        save(RUN / 'result.json', result)
        print(result, flush=True)
    except Exception:
        save(RUN / 'failure.json', dict(traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
