"""Լ�������ϵ�����պ�·�����������˷�Χ�������޶���ѧ���֡�"""
from types import SimpleNamespace
import mujoco
import numpy as np
from scipy.optimize import least_squares
from qualified_closure_v1.geometry import linkage, collisions, CONNECT_TOLERANCE_M
from qualified_closure_v1.geometry import SAMPLE_COUNT, MAX_SOLVER_EVALUATIONS, SIDES
from qualified_closure_v1.policy import summarize
from qualified_execution_v1.environment import state
from qualified_execution_v1.contact_audit import restored
from qualified_task_v1.integrity import fingerprint, unchanged
from routecheck.clone import clone_robot
from cm_geometry import place_robot

SPRING_SAMPLES = 17
ENVELOPE_DRIVER_SAMPLES = 41
SOLVER_TOLERANCE = 1e-12


def residual(model, data, *, info, values):
    data.qpos[info['addresses']] = values
    mujoco.mj_kinematics(model, data)
    eq = info['eq']
    first, second = int(model.eq_obj1id[eq]), int(model.eq_obj2id[eq])
    a = data.xpos[first] + data.xmat[first].reshape(3, 3) @ model.eq_data[eq, :3]
    b = data.xpos[second] + data.xmat[second].reshape(3, 3) @ model.eq_data[eq, 3:6]
    return a - b


def solve_side(model, data, *, side, angle, previous=None, spring=None):
    info = linkage(model, side)
    data.joint(f'{side}_driver_joint').qpos[0] = angle
    limits = info['bounds']
    initial = np.array(previous if previous is not None else [-angle, angle, -angle])
    initial = np.clip(initial, limits[:, 0], limits[:, 1])
    indexes = [0, 1, 2] if spring is None else [0, 2]
    if spring is not None:
        initial[1] = spring
    def objective(values):
        candidate = initial.copy()
        candidate[indexes] = values
        return residual(model, data, info=info, values=candidate)
    solved = least_squares(objective, initial[indexes],
                           bounds=(limits[indexes, 0], limits[indexes, 1]),
                           ftol=SOLVER_TOLERANCE, xtol=SOLVER_TOLERANCE, gtol=SOLVER_TOLERANCE,
                           max_nfev=MAX_SOLVER_EVALUATIONS)
    initial[indexes] = solved.x
    error = residual(model, data, info=info, values=initial)
    valid = bool(solved.success and np.isfinite(error).all()
                 and np.max(np.abs(error)) <= CONNECT_TOLERANCE_M)
    return dict(valid=valid, joints=initial.tolist(), connect_error_m=float(np.max(np.abs(error))),
                evaluations=int(solved.nfev))


def configuration(model, values, *, source, angle, previous=None, spring=None):
    data = restored(model, values)
    solved = {side: solve_side(model, data, side=side, angle=angle,
                               previous=previous[side] if previous else None, spring=spring)
              for side in SIDES}
    valid = all(row['valid'] for row in solved.values())
    mujoco.mj_forward(model, data)
    return dict(angle_rad=float(angle), spring_rad=spring, valid=valid, linkage=solved,
                contacts=collisions(model, data, source) if valid else None)


def nominal(model, values, *, source, angles):
    rows, previous = [], None
    for angle in angles:
        row = configuration(model, values, source=source, angle=float(angle), previous=previous)
        rows.append(row)
        if row['valid']:
            previous = {side: row['linkage'][side]['joints'] for side in SIDES}
    return rows


def envelope(model, values, *, source, angle_range):
    joint = model.joint('right_spring_link_joint').id
    low, high = model.jnt_range[joint]
    rows = []
    for angle in np.linspace(*angle_range, ENVELOPE_DRIVER_SAMPLES):
        for spring in np.linspace(low, high, SPRING_SAMPLES):
            rows.append(configuration(model, values, source=source,
                                      angle=float(angle), spring=float(spring)))
    return rows


def sweep(env, item, *, command, sample_count=SAMPLE_COUNT):
    command = np.asarray(command, dtype=float)
    if sample_count < 2 or command.shape != (6,) or not np.isfinite(command).all():
        raise ValueError('Finite six-joint command and at least two samples required')
    before, model = fingerprint(env), env.mj_model
    data = restored(model, state(env))
    place_robot(clone_robot(env.robot), env, data, q=command)
    values = state(SimpleNamespace(mj_model=model, mj_data=data))
    limits = model.jnt_range[model.joint('right_driver_joint').id].copy()
    np.testing.assert_array_equal(model.jnt_range[model.joint('left_driver_joint').id], limits)
    angles = np.linspace(*limits, sample_count)
    rows = nominal(model, values, source=item['source'], angles=angles)
    bounds = envelope(model, values, source=item['source'], angle_range=limits)
    result = summarize(rows, expected_count=sample_count)
    valid_bounds = [row for row in bounds if row['valid']]
    collision_bounds = [row for row in valid_bounds if row['contacts']]
    result['passed'] = result['passed'] and bool(valid_bounds) and not collision_bounds
    result.update(rows=rows, envelope=bounds, envelope_valid=len(valid_bounds),
                  envelope_collisions=len(collision_bounds),
                  isolation=unchanged(before, fingerprint(env)), command=command.tolist(),
                  method='free_linkage_nominal_path_and_spring_envelope', integration_steps=0,
                  adaptive_dynamics_covered=False, continuous_collision_proven=False,
                  historical_terminal_fingers_used=False)
    return result
