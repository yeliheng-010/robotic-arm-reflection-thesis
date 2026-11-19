"""每个数组任务只执行一个独立条件，不重试、不改旧实验。"""
import os
import signal
import traceback
from pathlib import Path
from unittest.mock import patch
from qualified_closure_dynamics_v1.protocol import read, save, sha, require

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent


def register():
    manifest = read(ROOT / 'manifest.json')
    require(manifest['execution_authorized'] is True, 'Batch not authorized')
    index = int(os.environ['SLURM_ARRAY_TASK_ID'])
    condition = manifest['conditions'][index]
    require(condition['index'] == index, 'Condition mismatch')
    for name, digest in manifest['identities'].items():
        require(sha(PROJECT / name) == digest, 'Input changed: ' + name)
    folder = ROOT / 'run' / f'{index:03d}'
    folder.mkdir(parents=True, exist_ok=False)
    save(folder / 'claim.json', dict(consumed=1, condition=condition,
         job=os.environ['SLURM_JOB_ID'], manifest_sha256=sha(ROOT / 'manifest.json')))
    return condition, folder


def stop_batch(message):
    try:
        save(ROOT / 'STOP.json', dict(reason=message, job=os.environ['SLURM_JOB_ID']))
    except FileExistsError:
        pass


def perturb(env, condition, folder):
    import mujoco
    import numpy as np
    from qualified_execution_v1.environment import state
    body = env.mj_model.body('PurpleCapsule')
    joint = int(body.jntadr[0])
    require(int(body.jntnum[0]) == 1, 'Expected one capsule joint')
    require(env.mj_model.jnt_type[joint] == mujoco.mjtJoint.mjJNT_FREE, 'Expected free joint')
    address = int(env.mj_model.jnt_qposadr[joint])
    original = env.mj_data.qpos[address:address + 3].copy()
    env.mj_data.qpos[address:address + 2] += condition['offset_xy_m']
    mujoco.mj_forward(env.mj_model, env.mj_data)
    save(folder / 'perturbation.json', dict(condition=condition, original_xyz=original.tolist(),
         modified_xyz=env.mj_data.qpos[address:address + 3].tolist()))
    with (folder / 'initial_state.npz').open('xb') as stream:
        np.savez_compressed(stream, state=state(env))


def interrupted(signum, frame):
    raise RuntimeError('Scheduler termination signal: ' + str(signum))


def run(condition, folder):
    from qualified_full_task_trial_v1.budget import limited
    from qualified_full_task_trial_v1 import worker as original
    from qualified_execution_v1.environment import opened
    case = read(PROJECT / 'qualified_task_v1/run/manifest.json')['cases']['978505']
    plan = read(PROJECT / original.PLAN)['plan']
    guard = {}
    result = dict(success=False, completed=False, physical_attempts=0, status='not_started')
    with limited() as budget:
        try:
            with opened(case, guard, static=False) as env:
                perturb(env, condition, folder)
                if (ROOT / 'STOP.json').exists():
                    result['status'] = 'skipped_batch_stop'
                else:
                    budget.begin_task(env)
                    save(folder / 'started.json', dict(stage='full_task', condition=condition))
                    result['physical_attempts'] = 1
                    with patch.object(original, 'RUN', folder):
                        result = original.trial(env, case, plan=plan, budget=budget)
                    result['status'] = 'completed' if result['success'] else 'task_failed'
        except Exception:
            result.update(status='engineering_failure', engineering_failure=traceback.format_exc())
        finally:
            budget.phase = 'blocked'
            result.update(condition=condition, native_counts=budget.counts, retries=0,
                          job=os.environ['SLURM_JOB_ID'], independent_audits=0)
            if result.get('engineering_failure') or (result.get('safety_error') or {}).get('type') == 'engineering_failure':
                result['status'] = 'engineering_failure'
                stop_batch(result)
            save(folder / 'guard.json', guard)
            save(folder / 'result.json', result)
    print({k: result.get(k) for k in ('status', 'success', 'steps', 'condition')}, flush=True)


def main():
    signal.signal(signal.SIGTERM, interrupted)
    try:
        condition, folder = register()
        if (ROOT / 'STOP.json').exists():
            save(folder / 'result.json', dict(status='skipped_batch_stop', success=False,
                 physical_attempts=0, condition=condition))
            return
        run(condition, folder)
    except Exception:
        stop_batch(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
