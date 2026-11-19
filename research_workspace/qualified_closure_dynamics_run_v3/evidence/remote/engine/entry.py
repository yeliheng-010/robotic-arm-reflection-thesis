"""v2入口：真实导入来源验证通过后才消耗独立claim。"""
import os
from contextlib import ExitStack
from unittest.mock import patch
from qualified_closure_dynamics_v3.protocol import (
    ROOT, RUN, PROJECT, read, save, sha, require, verify_authorization,
    read_snapshot, validate_runtime, consume)
from qualified_closure_dynamics_v3.guarded_imports import zero_motion, load_runtime


def preclaim():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    auth = verify_authorization(ROOT / 'authorization.json')
    with zero_motion() as counts:
        load_runtime()
        validate_runtime(read_snapshot())
        require(not any(counts.values()), 'Simulation attempted before claim')
    return auth


def run_environment(auth, gate):
    import mujoco
    from qualified_execution_v1.environment import opened
    from qualified_closure_dynamics_v1.initial import prepare
    from qualified_closure_dynamics_v1.capture import Sink
    from qualified_closure_dynamics_v1.backend import Backend
    from qualified_closure_dynamics_v1.worker import run_loop
    from qualified_closure_dynamics_v1.protocol import inventory
    case = read(PROJECT / 'qualified_task_v1/run/manifest.json')['cases']['978505']
    parent = PROJECT / 'qualified_closure_reachability_v1/run'
    inputs, expected = read(parent / 'input.json'), read(parent / 'parameters.json')
    save(RUN / 'imports.json', validate_runtime(read_snapshot()))
    with ExitStack() as lifetime:
        gate.stage = 'setup'
        env = lifetime.enter_context(opened(case, {}, static=False))
        gate.stage = 'blocked'
        require(gate.setup_steps == 500, 'Unexpected setup count')
        rejected = prepare(env, inputs, expected=expected, folder=RUN)
        mujoco.mj_saveModel(env.mj_model, str(RUN / 'model.mjb'))
        backend = Backend(env, gate, inputs=inputs, source=case['item']['source'], initial_rejections=rejected)
        save(RUN / 'metadata.json', dict(mujoco_version=mujoco.__version__, source=case['item']['source'],
             model_sha256=sha(RUN / 'model.mjb'), model_fields=backend.model_fields,
             timestep=float(env.mj_model.opt.timestep), integrator=int(env.mj_model.opt.integrator),
             initial_time=backend.start_time, inputs=inputs, safety_gate_changed=False))
        gate.stage = 'task'
        try:
            result = run_loop(backend, Sink(RUN, backend))
        finally:
            gate.stage = 'blocked'
        validate_runtime(read_snapshot())
        verify_authorization(ROOT / 'authorization.json')
        save(RUN / 'result.json', dict(**result, setup_steps=gate.setup_steps,
             task_step_requests=gate.task_steps, source_preserved=True, production_ready=False))
        save(RUN / 'primary_inventory.json', inventory(RUN))


def main():
    auth = preclaim()
    consume(auth, RUN)
    import mujoco
    import grasp_process as grasp
    from qualified_closure_dynamics_v1.limits import guarded, forbid
    with guarded(mujoco) as gate, patch.object(grasp.GraspFlow, 'close_gripper', forbid):
        try:
            run_environment(auth, gate)
        except Exception as error:
            gate.stage = 'blocked'
            save(RUN / 'failure.json', dict(error=type(error).__name__ + ': ' + str(error),
                 setup_step_requests=gate.setup_steps, task_step_requests=gate.task_steps))
            raise


if __name__ == '__main__':
    main()
