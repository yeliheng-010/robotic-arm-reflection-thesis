import traceback
import numpy as np
from qualified_execution_v1.environment import opened, state
from qualified_execution_v1.common import RUN, read, save, verify, case, plan
from qualified_execution_v1.register import claim
from qualified_execution_v1 import runtime, policy
from qualified_task_v1.observer import observe, ObservationRejected
from reflection.errors import TaskAbort
from reflection.monitors import evaluate_placement
from live_telemetry import capture


def snapshot(env, folder):
    with (folder/'final_state.npz').open('xb') as stream:
        np.savez_compressed(stream, state=state(env), robot_q=env.robot.get_joint())


def trial(env, item, *, folder, guard):
    trace, stages, counts = [], [], dict(steps=0)
    result = dict(completed=False, safety_error=None, model_calls=0, training_runs=0,
        physical_attempts=1, online_model_decisions=False, training_eligible=False)
    initial_quat = env.mj_data.body(item['item']['source']).xquat.copy()
    try:
        observe(env, item['config'], folder=folder/'initial_observation')
        initial = policy.initial_allowed(initial_qualified=True, state_matches=True,
            preflight_passed=read(RUN/'preflight/result.json')['passed'],
            audit_passed=read(RUN/'preflight_audit.json')['passed'])
        assert initial
        with capture() as telemetry:
            try:
                runtime.execute(runtime.native_flow(env, plan()), item, plan=plan(), folder=folder,
                    trace=trace, stages=stages, counts=counts)
                result['completed'] = True
            finally:
                save(folder/'telemetry.json', dict(rows=telemetry.rows, stride=10))
    except TaskAbort as error:
        result['safety_error'] = error.report.to_dict()
    except ObservationRejected:
        result['safety_error'] = dict(type='initial_observation_rejected')
    except Exception:
        result['safety_error'] = dict(type='engineering_failure', traceback=traceback.format_exc())
    physical, evaluation, _ = evaluate_placement(env, item['item']['source'], item['item']['destination'], initial_quat)
    result.update(physical_placement=bool(physical), evaluation=evaluation, stages=stages, **counts)
    result['success'] = policy.accepted(completed=result['completed'], physical_placement=bool(physical),
        safety_error=result['safety_error'])
    save(folder/'private_paths.json', trace)
    save(folder/'guard.json', guard)
    save(folder/'initial_quat.json', initial_quat.tolist())
    snapshot(env, folder)
    return result


def final_observation(env, item, *, folder):
    try:
        observe(env, item['config'], folder=folder/'final_observation')
        return dict(qualified=True, model_input_published=False, training_eligible=False)
    except ObservationRejected:
        return dict(qualified=False, model_input_published=False, training_eligible=False)


def main():
    claim()
    folder = RUN/'physical'
    folder.mkdir(parents=True, exist_ok=False)
    item, guard = case(), {}
    with opened(item, guard, static=False) as env:
        result = trial(env, item, folder=folder, guard=guard)
        save(folder/'result.json', result)
        published = final_observation(env, item, folder=folder)
        save(folder/'publication.json', published)
    verify()
    print({k: result[k] for k in ('success', 'completed', 'physical_placement', 'stages', 'steps')}, flush=True)


if __name__ == '__main__':
    main()
