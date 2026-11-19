"""仅复用静态预检，不启动任何模型或执行器作业。"""
import os
from reflection.__main__ import bootstrap
bootstrap()
from qualified_closure_feedback_v1.preflight import evaluate
from qualified_checkpoint_preflight_v1.protocol import RUN, read, save, source_action, reserve, verify
from qualified_checkpoint_preflight_v1.guards import static_scope


def run(folder):
    inputs = read(RUN / 'input.json')
    assert inputs['action'] == source_action()
    with static_scope() as guard:
        result = evaluate(inputs['action'], history=inputs['history'], geometry=inputs['geometry'], folder=folder)
    assert guard['blocked_task_integration_requests'] == guard['blocked_gripper_close_requests'] == 0
    save(folder / 'zero_motion_guard.json', guard)
    save(folder / 'result.json', result)
    return result


def main():
    assert os.environ.get('SLURM_JOB_ID')
    reserve()
    result = run(RUN / 'preflight')
    verify()
    save(RUN / 'result.json', dict(**result, preflight_sessions=1, model_calls=0,
         physical_attempts=0, training_runs=0, physical_registered=False,
         task_integration_requests=0, ready_for_physical_execution=False))
    print(result, flush=True)


if __name__ == '__main__':
    main()
