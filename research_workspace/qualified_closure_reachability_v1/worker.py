"""仅复核5个旧碰撞构型，无包络搜索与任务积分。"""
import os
from types import SimpleNamespace
from reflection.__main__ import bootstrap
bootstrap()
import numpy as np
from qualified_execution_v1.environment import opened, state
from qualified_execution_v1.contact_audit import restored
from qualified_task_v1.integrity import fingerprint, unchanged
from qualified_checkpoint_preflight_v1.guards import static_scope
from cm_geometry import place_robot
from routecheck.clone import clone_robot
from qualified_closure_reachability_v1 import parameters
from qualified_closure_reachability_v1.probe import inspect_row
from qualified_closure_reachability_v1.common import PROJECT, RUN, PARENT, read, save, sha, verify


def main():
    manifest = verify()
    save(RUN / 'diagnostic_claim.json', dict(consumed=1, input_sha256=manifest['input_sha256']))
    inputs = read(RUN / 'input.json')
    case = read(PROJECT / 'qualified_task_v1/run/manifest.json')['cases']['978505']
    plan = read(PARENT / 'run/preflight/private_plan.json')['plan']
    with static_scope() as guard, opened(case, {}, static=True) as env:
        before = fingerprint(env)
        meta = dict(joints=parameters.joint_rows(env.mj_model), equalities=parameters.equality_rows(env.mj_model),
                    actuator=parameters.actuator_row(env.mj_model))
        controls = parameters.controller(env, plan)
        data = restored(env.mj_model, state(env))
        place_robot(clone_robot(env.robot), env, data, q=np.asarray(inputs['command']))
        base = state(SimpleNamespace(mj_model=env.mj_model, mj_data=data))
        rows = [inspect_row(env, base, entry=entry, parameters=meta, controls=controls,
                            source=case['item']['source']) for entry in inputs['configurations']]
        isolation = unchanged(before, fingerprint(env))
    assert guard['blocked_task_integration_requests'] == guard['blocked_gripper_close_requests'] == 0
    save(RUN / 'parameters.json', meta)
    save(RUN / 'controls.json', controls)
    save(RUN / 'result.json', dict(rows=rows, isolation=isolation, guard=guard, job=os.environ['SLURM_JOB_ID'],
         fixed_configurations=5, zero_velocity_force_probes=15, new_model_calls=0, physical_attempts=0, training_runs=0,
         reachability_proven=False, unreachability_proven=False, safety_gate_changed=False,
         parent_rejection_preserved=True))
    verify()
    print(dict(fixed_configurations=len(rows), isolation=isolation, guard=guard,
               force_probes=15, reachability='not_proven_by_static_constraints'), flush=True)


if __name__ == '__main__':
    main()
