"""只重建已有状态的夹爪运动学，不运行完整环境。"""
import os
import numpy as np
import mujoco
from qualified_initial_state_v1 import model as helper
from qualified_initial_state_v1.guards import kinematics_only
from qualified_initial_state_v1.common import (
    RUN, XML, PARAMETERS, read, save, sha, require, verify, input_states, recorded_equalities)

NUMERIC_REPRODUCTION_TOLERANCE = 1e-12


def inspect(model, states, parameters):
    helper.verify_model(model, parameters)
    layout = helper.check_state_layout(model)
    values = {name: helper.qpos_from_state(state, parameters) for name, state in states.items()}
    for row in parameters['joints']:
        require(values['before'][row['name']] == values['after'][row['name']], 'Finger changed')
    rows = {name: helper.evaluate(model, state, parameters) for name, state in states.items()}
    recorded = recorded_equalities()
    for row in rows['after']:
        np.testing.assert_allclose(recorded[row['id']]['residual'], row['world'],
                                   atol=NUMERIC_REPRODUCTION_TOLERANCE, rtol=0)
    for before, after in zip(rows['before'], rows['after']):
        np.testing.assert_allclose(before['local'], after['local'],
                                   atol=NUMERIC_REPRODUCTION_TOLERANCE, rtol=0)
        require(not before['passed'] and not after['passed'], 'Unexpected initial constraint status')
    bounds = [bool(row['range'][0] <= values['after'][row['name']] <= row['range'][1])
              for row in parameters['joints']]
    save(RUN / 'reconstructed_report_subset.json', dict(finger_limits=bounds, equalities=recorded,
        reconstruction_only=True, replaces_original=False, rejection=['initial_constraints']))
    return dict(states=rows, layout=layout, fingers_unchanged=True, original_equals_before=True,
        residual_preexists_placement=True, rigid_rotation_preserves_local_residual=True,
        frozen_state_is_not_valid_for_current_initial_gate=True, finger_limits=bounds,
        recorded_after_reproduced=True, numerical_comparison_tolerance=NUMERIC_REPRODUCTION_TOLERANCE)


def main():
    checked = verify()
    save(RUN / 'diagnostic_claim.json', dict(consumed=1, integration_budget=0, job=os.environ['SLURM_JOB_ID']))
    text = helper.isolated_xml(XML)
    with (RUN / 'isolated_gripper.xml').open('x', encoding='utf-8') as stream:
        stream.write(text)
    with kinematics_only(text) as counts:
        try:
            model = mujoco.MjModel.from_xml_string(text)
            result = inspect(model, input_states(), read(PARAMETERS))
        except Exception as error:
            save(RUN / 'failure.json', dict(error=type(error).__name__ + ': ' + str(error), counts=counts))
            raise
    require(all(counts[key] == 0 for key in ('integration', 'scene', 'rendering', 'forbidden_model', 'forward')),
            'Unexpected operation')
    result.update(passed=True, job=os.environ['SLURM_JOB_ID'], counts=counts, imports=checked,
        isolated_model_only=True, contact_geometry_present=False, placeholder_root_inertia=True,
        full_scene_reconstructed=False, dynamics_validated=False, safety_gate_changed=False)
    save(RUN / 'result.json', result)
    save(RUN / 'inventory.json', {p.name: sha(p) for p in RUN.iterdir() if p.is_file()})
    print(dict(passed=True, counts=counts, residual_preexists_placement=True,
               original_initial_gate_passed=False), flush=True)


if __name__ == '__main__':
    main()
