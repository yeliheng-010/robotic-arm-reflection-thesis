from pathlib import Path
import traceback
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import mujoco
from cv_select import scene
from cv_rgb import compare
from pose_fresh_v1.observe import paused
from sensor_rgb_diagnostic_v1.worker import frames, comparisons
from sensor_independent_v2.common import verify
from surface_grasp_v1.common import read, save, sha

ROOT = Path(__file__).resolve().parent
RUN = ROOT / 'run'
SOURCE = ROOT.parent / 'sensor_independent_v2/run'
SEED = 978401


def selected(rows):
    measured = [r for r in rows if 'rgb' in r]
    predicates = (lambda r: r['rgb']['passed'], lambda r: not r['rgb']['passed'],
                  lambda r: r['rgb']['max_channel_delta'] > 10)
    return list(dict.fromkeys(next(r['index'] for r in measured if predicate(r)) for predicate in predicates))


def archived_comparisons(values, archived):
    return {key: {name: compare(archived[key], image) for name, image in values.items()}
            for key in ('before', 'after')}


def run_case(row, config):
    folder = RUN / str(row['index'])
    folder.mkdir(exist_ok=False)
    source = SOURCE / str(SEED)
    boxes = read(source / 'boxes.json')
    with scene(config) as (env, segment):
        with np.load(source / 'initial_state.npz') as data:
            mujoco.mj_setState(env.mj_model, env.mj_data, data['state'], mujoco.mjtState.mjSTATE_INTEGRATION)
        mujoco.mj_forward(env.mj_model, env.mj_data)
        with paused(env, folder):
            groups = env.mj_model.geom_group.copy()
            values, actual = frames(env, segment, camera=row['camera'], boxes=boxes)
            np.testing.assert_array_equal(groups, env.mj_model.geom_group)
    with (folder / 'rgb.npz').open('xb') as stream:
        np.savez_compressed(stream, **values)
    with np.load(source / f'rgb_{row["index"]}.npz') as archived:
        cross = archived_comparisons(values, archived)
    result = dict(index=row['index'], original_rgb_check=row['rgb'], actual_samples=actual,
        comparisons=comparisons(values), archived_comparisons=cross, geom_group_restored=True,
        arrays_sha256=sha(folder / 'rgb.npz'), private_only=True)
    save(folder / 'result.json', result)
    return result


def identities(manifest):
    values = dict(manifest['identities'])
    for folder in (ROOT, ROOT.parent / 'sensor_rgb_diagnostic_v1'):
        values.update({str(p): sha(p) for p in folder.iterdir()
                       if p.suffix in ('.py', '.sbatch') or p.name == 'PLAN.md'})
    return values


def main():
    manifest = verify()
    rows = read(SOURCE / str(SEED) / 'observations.json')
    indices = selected(rows)
    RUN.mkdir(exist_ok=False)
    names = ['initial_state.npz', 'boxes.json', 'observations.json'] + [f'rgb_{i}.npz' for i in indices]
    inputs = {str(SOURCE / str(SEED) / n): sha(SOURCE / str(SEED) / n) for n in names}
    save(RUN / 'started.json', dict(indices=indices, inputs=inputs, identities=identities(manifest)))
    try:
        result = {str(i): run_case(rows[i], manifest['configs'][str(SEED)]) for i in indices}
        assert all(sha(p) == digest for p, digest in inputs.items())
        verify()
        save(RUN / 'result.json', result)
        print({k: v['comparisons'] for k, v in result.items()}, flush=True)
    except Exception:
        save(RUN / 'failure.json', dict(traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
