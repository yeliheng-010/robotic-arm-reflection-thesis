"""真实动力学入口：缺独立授权即在导入仿真前拒绝。"""
import os
import sys
from contextlib import ExitStack
from unittest.mock import patch
from qualified_closure_dynamics_v1.protocol import ROOT, PROJECT, RUN, read, save, sha, claim, verify, require, inventory


def authorization():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    auth = read(ROOT / 'authorization.json')
    proposal = read(ROOT / 'preparation_manifest.json')
    require(auth['preparation_sha256'] == sha(ROOT / 'preparation_manifest.json'), 'Preparation mismatch')
    require(auth['identities'] == proposal['identities'], 'Authorization identity set mismatch')
    verify(auth)
    return claim(ROOT / 'authorization.json', RUN)


def imported_sources(auth):
    rows = {}
    for module in list(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if not isinstance(name, str):
            continue
        from pathlib import Path
        path = Path(name).resolve()
        if path.is_relative_to(PROJECT) and path.is_file():
            require(auth['identities'].get(str(path)) == sha(path), 'Unbound runtime source: ' + str(path))
            rows[str(path)] = sha(path)
    return rows


def run_environment(auth, gate):
    import mujoco
    from qualified_execution_v1.environment import opened
    from qualified_closure_dynamics_v1.initial import prepare
    from qualified_closure_dynamics_v1.capture import Sink
    from qualified_closure_dynamics_v1.backend import Backend
    from qualified_closure_dynamics_v1.worker import run_loop
    case = read(PROJECT / 'qualified_task_v1/run/manifest.json')['cases']['978505']
    parent = PROJECT / 'qualified_closure_reachability_v1/run'
    inputs, expected = read(parent / 'input.json'), read(parent / 'parameters.json')
    save(RUN / 'imports.json', imported_sources(auth))
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
            report = run_loop(backend, Sink(RUN, backend))
        finally:
            gate.stage = 'blocked'
        verify(auth)
        save(RUN / 'result.json', dict(**report, setup_steps=gate.setup_steps,
             task_step_requests=gate.task_steps, source_preserved=True, production_ready=False))
        save(RUN / 'primary_inventory.json', inventory(RUN))


def main():
    auth = authorization()
    from reflection.__main__ import bootstrap
    bootstrap()
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
