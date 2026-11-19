import os
import traceback
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import cv_select
from cv_policy import REQUIRED
from sd_inventory import root_boxes
from visibility_calibration_v1 import capture
from pose_fresh_v1.observe import paused
from pose_fresh_v1 import estimate, evaluate
from camera_joint_v1.policy import SEEDS, NOISE_PREFIX
from camera_joint_v1.search import run as search
from camera_joint_v1.common import RUN, read, save, sha, files, verify


def capture_pose(env, renderer, *, config, boxes, camera, folder):
    snapshot = dict(case=dict(item=dict(seed=config['seed'], source='PurpleCapsule'), config=config))
    with patch.object(capture, 'SEED_PREFIX', NOISE_PREFIX):
        row, clouds = capture.view(env, renderer, camera=camera, boxes=boxes, snapshot=snapshot,
            phase_id=0, index=0, folder=folder / 'view_0')
    assert row['calibration_passed'] and row['report']['gate']['passed']
    row.update(full_frame_qualified=True, training_eligible=False, control_eligible=False)
    save(folder / 'views.json', [row])
    cv_select.image(env, folder / 'qualified.png')
    save(folder / 'fits.json', estimate.run([row], {0: clouds}))
    geom = env.mj_model.geom('purple_capsule').id
    save(folder / 'private_truth.json', dict(center=env.mj_data.geom_xpos[geom].tolist(),
        axis=env.mj_data.geom_xmat[geom].reshape(3, 3)[:, 2].tolist(), private_simulation_truth=True))
    return evaluate.run(folder)


def experiment(config, folder):
    results, cache = {}, {}
    with cv_select.scene(config) as (env, renderer), paused(env, folder):
        all_boxes = root_boxes(env.mj_model, env.mj_data)
        boxes = {name: all_boxes[name] for name in REQUIRED}
        save(folder / 'boxes.json', boxes)
        for method in ('original', 'joint'):
            output = folder / method
            output.mkdir(exist_ok=False)
            attempts = search(env, renderer, config=config, boxes=boxes, method=method, cache=cache)
            qualified = bool(attempts[-1]['accepted'])
            result = dict(qualified=qualified, candidates=len(attempts),
                measured=sum('gate' in r for r in attempts),
                reused=sum(r.get('cache_reused', False) for r in attempts),
                measured_new=sum('gate' in r and not r.get('cache_reused', False) for r in attempts))
            save(output / 'selection.json', dict(attempts=attempts, accepted=qualified))
            if qualified:
                result.update(capture_pose(env, renderer, config=config, boxes=boxes,
                    camera=attempts[-1]['camera'], folder=output))
            results[method] = result
    return results


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
        methods = experiment(config, folder) if eligible else {}
        verify()
        result = dict(seed=seed, geometry_accepted=eligible, methods=methods,
            evidence=files(folder), task_motion_attempts=0, model_calls=0, training_runs=0)
        save(folder / 'result.json', result)
        print(dict(seed=seed, methods=methods), flush=True)
    except Exception:
        save(folder / 'failure.json', dict(traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
