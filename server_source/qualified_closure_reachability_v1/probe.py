"""直接恢复旧构型，并在零速度私有副本上取瞬时力。"""
import mujoco
import numpy as np
from qualified_execution_v1.contact_audit import restored
from qualified_execution_v1.environment import state
from qualified_closure_v1.geometry import collisions
from qualified_closure_reachability_v1.parameters import SIDES


def rebuild(model, base, saved):
    data = restored(model, base)
    for side in SIDES:
        data.joint(f'{side}_driver_joint').qpos[0] = saved['angle_rad']
        for part, value in zip(('coupler', 'spring_link', 'follower'), saved['linkage'][side]['joints']):
            data.joint(f'{side}_{part}_joint').qpos[0] = value
    mujoco.mj_forward(model, data)
    return data


def constraints(model, data, *, joints, equalities):
    ranges = [dict(name=row['name'], position=float(data.qpos[row['qpos_address']]),
                  within_range=bool(row['range'][0] <= data.qpos[row['qpos_address']] <= row['range'][1]))
              for row in joints]
    residuals = []
    for row in equalities:
        index = row['id']
        if row['type'] == int(mujoco.mjtEq.mjEQ_CONNECT):
            left, right = int(model.eq_obj1id[index]), int(model.eq_obj2id[index])
            a = data.xpos[left] + data.xmat[left].reshape(3, 3) @ model.eq_data[index, :3]
            b = data.xpos[right] + data.xmat[right].reshape(3, 3) @ model.eq_data[index, 3:6]
            residuals.append(dict(id=index, type='connect', active=bool(data.eq_active[index]),
                                  maximum_abs=float(np.max(np.abs(a - b)))))
        else:
            x, y = [float(data.joint(name).qpos[0]) for name in row['names']]
            delta = x - sum(coef * y ** power for power, coef in enumerate(row['data'][:5]))
            residuals.append(dict(id=index, type='driver_joint_equality', active=bool(data.eq_active[index]), maximum_abs=abs(delta)))
    return dict(joints=ranges, equalities=residuals)


def forces(model, data, *, actuator, joints, control):
    data.qvel[:] = 0
    data.ctrl[actuator['id']] = control
    mujoco.mj_forward(model, data)
    return dict(control=float(control), actuator_length=float(data.actuator_length[actuator['id']]),
        actuator_velocity=float(data.actuator_velocity[actuator['id']]),
        actuator_force=float(data.actuator_force[actuator['id']]),
        joint_forces=[dict(name=row['name'], qpos=float(data.qpos[row['qpos_address']]),
            passive=float(data.qfrc_passive[row['dof_address']]),
            actuator=float(data.qfrc_actuator[row['dof_address']])) for row in joints],
        zero_velocity_counterfactual=True, trajectory_or_equilibrium_solution=False)


def inspect_row(env, base, *, entry, parameters, controls, source):
    saved, model = entry['saved'], env.mj_model
    data = rebuild(model, base, saved)
    contacts = collisions(model, data, source)
    assert contacts == saved['contacts']
    checked = constraints(model, data, joints=parameters['joints'], equalities=parameters['equalities'])
    aid = parameters['actuator']['id']
    gain = float(model.actuator_gainprm[aid, 0])
    bias = model.actuator_biasprm[aid]
    reference = -(bias[0] + bias[1] * data.actuator_length[aid]) / gain
    requested = [('first_command', controls['first_command']), ('zero_speed_actuator_balance_reference', reference),
                 ('last_command', controls['last_command'])]
    probes = [dict(label=label, **forces(model, data, actuator=parameters['actuator'],
                                        joints=parameters['joints'], control=control)) for label, control in requested]
    return dict(envelope_index=entry['index'], angle_rad=saved['angle_rad'], spring_rad=saved['spring_rad'],
        contacts=contacts, constraints=checked, force_probes=probes,
        reference_control_within_default_command_range=bool(controls['first_command'] <= reference <= controls['last_command']),
        dynamic_reachability='not_determined')
