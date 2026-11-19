"""执行与零步验证共享恢复/采集路径；验证分支没有task阶段。"""
import os
from qualified_closure_mjb_v1.protocol import (
    PROJECT, proposal, read, save, sha, require, verify_sources, inventory)


def metadata(backend, initial, *, mode):
    import mujoco
    plan = proposal()
    return dict(mode=mode, model_fields=backend.model_fields, model_path=plan['model']['path'],
        model_sha256=plan['model']['sha256'], candidate_sha256=plan['candidate']['sha256'],
        mujoco_version=mujoco.__version__, timestep=float(backend.model.opt.timestep),
        integrator=int(backend.model.opt.integrator), solver=int(backend.model.opt.solver),
        initial_time=backend.start_time, initial_tcp=backend.initial_tcp.tolist(),
        inputs=backend.inputs, source=plan['source'], initial_rejections=initial,
        safety_gate_changed=False, production_ready=False)


def trajectory(resources, folder, *, mode):
    from qualified_closure_mjb_v1.restore import prepare
    from qualified_closure_mjb_v1.backend import Backend
    from qualified_closure_mjb_v1.worker import run_loop, reasons
    from qualified_closure_dynamics_v1.capture import Sink
    model, data, initial = prepare(resources, folder)
    backend = Backend(model, data, gate=resources.gate,
        inputs=read(PROJECT/proposal()['control']['inputs']), initial_rejections=initial)
    save(folder/'metadata.json', metadata(backend, initial, mode=mode))
    sink = Sink(folder, backend)
    if mode == 'verification':
        row = backend.observe()
        sink.observed(0, row)
        return dict(completed_steps=0, observed_steps=0, uncertain_step=None,
                    reasons=reasons(row) or ['verification_only'], error=None)
    require(mode == 'execution', 'Invalid trace mode')
    resources.gate.stage = 'task'
    try:
        return run_loop(backend, sink)
    finally:
        resources.gate.stage = 'blocked'


def run(folder, *, mode, imports):
    from qualified_closure_mjb_v1.resources import guarded
    from qualified_scene_candidate_v1.common import loaded_sources
    with guarded() as resources:
        try:
            result = trajectory(resources, folder, mode=mode)
            identities = verify_sources()
            loaded = loaded_sources(identities)
            require(all(resources.counts[k] == 0 for k in
                        ('forbidden', 'reset', 'compile', 'rendering', 'planning', 'optimizer', 'close')),
                    'Forbidden runtime action')
            require(resources.counts['binary_load'] == resources.counts['live_forward'] == 1,
                    'Unexpected restoration history')
            save(folder/'loaded_sources.json', loaded)
            save(folder/'result.json', dict(**result, mode=mode, job=os.environ['SLURM_JOB_ID'],
                setup_steps=0, task_step_requests=resources.gate.requests, task_step_returns=resources.gate.returns,
                counts=resources.summary(), import_counts=imports['counts'], gpu_profile=imports['gpu_profile'],
                verified_identities=len(identities), production_ready=False))
        except Exception as error:
            save(folder/'failure.json', dict(error=type(error).__name__+': '+str(error),
                 counts=resources.summary(), mode=mode))
            raise
    save(folder/'primary_inventory.json', inventory(folder))
    print(dict(mode=mode, **result, counts=resources.summary()), flush=True)
