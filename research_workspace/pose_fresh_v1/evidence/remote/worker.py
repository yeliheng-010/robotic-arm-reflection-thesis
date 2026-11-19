"""一布局一进程；已启动目录绝不自动重跑。"""
import os
import traceback
from reflection.__main__ import bootstrap
bootstrap()
from pose_fresh_v1 import observe, estimate, evaluate
from pose_fresh_v1.policy import SEEDS
from pose_fresh_v1.common import RUN, save, sha, files, verify


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
        captured = observe.run(config, folder) if eligible else None
        result = dict(seed=seed, geometry_accepted=eligible, qualified=captured is not None,
                      task_motion_attempts=0, model_calls=0, training_runs=0)
        if captured is not None:
            rows, clouds = captured
            save(folder / 'fits.json', estimate.run(rows, clouds))
            result.update(evaluate.run(folder))
        verify()
        result['evidence'] = files(folder)
        save(folder / 'result.json', result)
        print(result, flush=True)
    except Exception:
        save(folder / 'failure.json', dict(traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
