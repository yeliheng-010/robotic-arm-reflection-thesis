import os
import traceback
from reflection.__main__ import bootstrap
bootstrap()
from cv_select import scene
from cv_policy import REQUIRED
from sd_inventory import root_boxes
from pose_fresh_v1.observe import paused
from sensor_independent_v1.sensor import paired
from observation_search_v1.search import run as collect
from observation_search_v1.common import RUN, SEEDS, save, sha, files, verify


def experiment(config, folder):
    with scene(config) as (env, segment), paused(env, folder):
        all_boxes = root_boxes(env.mj_model, env.mj_data)
        boxes = {name: all_boxes[name] for name in REQUIRED}
        save(folder / 'boxes.json', boxes)
        with paired(env, segment) as (resources, actual_samples):
            result = collect(env, resources, config=config, boxes=boxes, folder=folder)
        result['actual_samples'] = actual_samples
    return result


def main():
    manifest = verify()
    seed = SEEDS[int(os.environ['SLURM_ARRAY_TASK_ID'])]
    folder = RUN / str(seed)
    folder.mkdir(exist_ok=False)
    save(folder / 'started.json', dict(seed=seed, job=os.environ.get('SLURM_JOB_ID'),
                                     manifest_sha256=sha(RUN / 'manifest.json')))
    try:
        config = manifest['configs'][str(seed)]
        eligible = config['geometry_accepted'] and config['compiled_check']['passed']
        outcome = experiment(config, folder) if eligible else {}
        verify()
        result = dict(seed=seed, geometry_accepted=eligible, **outcome, evidence=files(folder),
                      task_motion_attempts=0, model_calls=0, training_runs=0)
        save(folder / 'result.json', result)
        print({k: v for k, v in result.items() if k != 'evidence'}, flush=True)
    except Exception:
        save(folder / 'failure.json', dict(traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
