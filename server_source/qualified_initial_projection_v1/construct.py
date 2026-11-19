"""仅构造新的几何候选初态；无环境、积分或动力学授权。"""
import os
import numpy as np
import mujoco
from qualified_initial_state_v1 import model as helper
from qualified_initial_state_v1.guards import kinematics_only
from qualified_closure_dynamics_v1.capture import write_npz
from qualified_initial_projection_v1.projection import construct, state_contract
from qualified_initial_projection_v1.common import (
    RUN, XML, PARAMETERS, read, save, sha, require, verify, input_states)


def inspect(model, source, parameters):
    helper.verify_model(model, parameters)
    layout = helper.check_state_layout(model)
    candidate, solutions = construct(model, source, parameters)
    if candidate is None:
        return dict(candidate_created=False, solutions=solutions, rejection='local_projection_failed')
    contract = state_contract(source, candidate, parameters)
    require(all(row['within_original_range'] for row in contract['joint_changes']), 'Range violation')
    connections = helper.evaluate(model, candidate, parameters)
    require(all(row['passed'] for row in connections), 'Final full 3D connection rejection')
    values = helper.qpos_from_state(candidate, parameters)
    eq = next(row for row in parameters['equalities'] if row['type'] == 2)
    x, y = (values[name] for name in eq['names'])
    driver_residual = x - sum(coef * y**power for power, coef in enumerate(eq['data'][:5]))
    require(abs(driver_residual) <= 1e-7, 'Driver equality rejection')
    write_npz(RUN / 'candidate_state.npz', dict(integration=candidate, reference=source))
    return dict(candidate_created=True, solutions=solutions, state_contract=contract, layout=layout,
        connections=connections, driver_equality_residual=driver_residual,
        passive_projection_only=True, reference_is_old_synthetic_after=True)


def main():
    checked = verify()
    save(RUN / 'construction_claim.json', dict(consumed=1, integration_budget=0, job=os.environ['SLURM_JOB_ID']))
    xml = helper.isolated_xml(XML)
    with (RUN / 'isolated_gripper.xml').open('x', encoding='utf-8') as stream:
        stream.write(xml)
    with kinematics_only(xml) as counts:
        try:
            model = mujoco.MjModel.from_xml_string(xml)
            result = inspect(model, input_states()['after'], read(PARAMETERS))
        except Exception as error:
            save(RUN / 'failure.json', dict(error=type(error).__name__ + ': ' + str(error), counts=counts))
            raise
    require(all(counts[key] == 0 for key in ('integration', 'scene', 'rendering', 'forbidden_model', 'forward')),
            'Unexpected operation')
    result.update(job=os.environ['SLURM_JOB_ID'], counts=counts, imports=checked,
        geometry_feasible=bool(result['candidate_created']), full_scene_checked=False,
        attach_recomputed=False, collisions_checked=False, dynamics_validated=False,
        production_ready=False, execution_authorized=False, safety_gate_changed=False)
    save(RUN / 'result.json', result)
    save(RUN / 'inventory.json', {p.name: sha(p) for p in RUN.iterdir() if p.is_file()})
    print(dict(candidate_created=result['candidate_created'], counts=counts,
               execution_authorized=False, production_ready=False), flush=True)


if __name__ == '__main__':
    main()
