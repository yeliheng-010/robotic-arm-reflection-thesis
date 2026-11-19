"""复用完整抓放流程，单次执行、失败即停，不运行测试或独立审计。"""
import os
import traceback
from pathlib import Path
from qualified_closure_dynamics_v1.protocol import read, save, sha, require

ROOT = Path(__file__).resolve().parent
PROJECT, RUN = ROOT.parent, ROOT / 'run'
PLAN = 'qualified_checkpoint_preflight_v1/run/preflight/private_plan.json'


def claim():
    auth = read(ROOT / 'authorization.json')
    require(auth['execution_authorized'] is True, 'Missing execution authorization')
    require(auth['full_task_attempts'] == 1, 'Only one attempt allowed')
    for path, digest in auth['identities'].items():
        require(sha(PROJECT / path) == digest, 'Changed input: ' + path)
    RUN.mkdir(exist_ok=False)
    save(RUN / 'claim.json', dict(consumed=1, job=os.environ.get('SLURM_JOB_ID'),
         authorization_sha256=sha(ROOT / 'authorization.json')))
    return auth


def snapshot(env):
    import numpy as np
    from qualified_execution_v1.environment import state
    with (RUN / 'final_state.npz').open('xb') as stream:
        np.savez_compressed(stream, state=state(env), robot_q=env.robot.get_joint())


def trial(env, case, *, plan, budget):
    from qualified_execution_v1 import runtime, policy
    from reflection.errors import TaskAbort
    from reflection.monitors import evaluate_placement
    from live_telemetry import capture
    trace, stages, counts = [], [], dict(steps=0)
    result = dict(completed=False, safety_error=None, physical_attempts=1,
                  model_calls=0, training_runs=0, training_eligible=False)
    initial_quat = env.mj_data.body(case['item']['source']).xquat.copy()
    try:
        with capture() as telemetry:
            try:
                runtime.execute(runtime.native_flow(env, plan), case, plan=plan,
                                folder=RUN, trace=trace, stages=stages, counts=counts)
                result['completed'] = True
            finally:
                budget.phase = 'blocked'
                save(RUN / 'telemetry.json', dict(rows=telemetry.rows, stride=10))
    except TaskAbort as error:
        result['safety_error'] = error.report.to_dict()
    except Exception:
        result['safety_error'] = dict(type='engineering_failure', traceback=traceback.format_exc())
    finally:
        budget.phase = 'blocked'
        snapshot(env)
        save(RUN / 'private_paths.json', trace)
        save(RUN / 'progress.json', dict(stages=stages, **counts))
    physical, evaluation, _ = evaluate_placement(
        env, case['item']['source'], case['item']['destination'], initial_quat)
    result.update(physical_placement=bool(physical), evaluation=evaluation, stages=stages, **counts)
    result['success'] = policy.accepted(completed=result['completed'],
        physical_placement=bool(physical), safety_error=result['safety_error'])
    return result


def main():
    auth = claim()
    from qualified_full_task_trial_v1.budget import limited
    from qualified_execution_v1.environment import opened
    case = read(PROJECT / 'qualified_task_v1/run/manifest.json')['cases']['978505']
    plan = read(PROJECT / PLAN)['plan']
    guard, result = {}, dict(success=False, completed=False, physical_attempts=0)
    with limited() as budget:
        try:
            with opened(case, guard, static=False) as env:
                budget.begin_task(env)
                result = trial(env, case, plan=plan, budget=budget)
        except Exception:
            result['engineering_failure'] = traceback.format_exc()
        finally:
            budget.phase = 'blocked'
            result.update(native_counts=budget.counts, job=os.environ.get('SLURM_JOB_ID'),
                          additional_tests=0, independent_audits=0, retries=0,
                          known_preflight_status=auth['known_preflight_status'],
                          skipped_gates=auth['skipped_gates'])
            save(RUN / 'guard.json', guard)
            save(RUN / 'result.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    main()
