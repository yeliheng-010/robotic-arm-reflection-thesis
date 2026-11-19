"""只修改新副本的6个被动角；MuJoCo仅用于运动学。"""
import numpy as np
import mujoco
from qualified_initial_state_v1.model import qpos_from_state
from qualified_initial_projection_v1.solver import solve_side

PARTS = ('coupler', 'spring_link', 'follower')
SIDES = ('right', 'left')


def objective_residual(model, data, *, side, angles):
    for part, value in zip(PARTS, angles):
        data.joint(f'{side}_{part}_joint').qpos[0] = value
    mujoco.mj_kinematics(model, data)
    index = SIDES.index(side)
    first, second = int(model.eq_obj1id[index]), int(model.eq_obj2id[index])
    a = data.xpos[first] + data.xmat[first].reshape(3, 3) @ model.eq_data[index, :3]
    b = data.xpos[second] + data.xmat[second].reshape(3, 3) @ model.eq_data[index, 3:6]
    return data.body('base').xmat.reshape(3, 3).T @ (a - b)


def construct(model, source, parameters):
    data = mujoco.MjData(model)
    values = qpos_from_state(source, parameters)
    for name, value in values.items():
        data.joint(name).qpos[:] = value
    joints = {row['name']: row for row in parameters['joints']}
    candidate, solutions = source.copy(), {}
    for side in SIDES:
        names = [f'{side}_{part}_joint' for part in PARTS]
        reference = np.array([values[name] for name in names])
        bounds = np.array([joints[name]['range'] for name in names])
        residual = lambda x: objective_residual(model, data, side=side, angles=x)
        solved = solve_side(reference, bounds, residual=residual)
        solutions[side] = solved
        if solved['accepted']:
            for name, angle in zip(names, solved['angles']):
                candidate[1 + joints[name]['qpos_address']] = angle
    accepted = all(row['accepted'] for row in solutions.values())
    return candidate if accepted else None, solutions


def state_contract(source, candidate, parameters):
    allowed = {1 + row['qpos_address'] for row in parameters['joints']
               if any(part in row['name'] for part in PARTS)}
    changed = set(np.flatnonzero(source != candidate).tolist())
    if not changed <= allowed:
        raise ValueError('Changed state outside passive finger angles')
    rows = []
    for row in parameters['joints']:
        address = 1 + row['qpos_address']
        old, new = float(source[address]), float(candidate[address])
        rows.append(dict(name=row['name'], old=old, new=new, delta=new - old,
                         within_original_range=bool(row['range'][0] <= new <= row['range'][1])))
    return dict(changed_state_indices=sorted(changed), allowed_state_indices=sorted(allowed),
                other_state_unchanged=True, joint_changes=rows)
