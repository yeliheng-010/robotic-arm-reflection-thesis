"""����ƽ��ָ��պϣ�Լ������뾲̬���������ƽ�����ѧ��"""
from types import SimpleNamespace
import mujoco
import numpy as np
from scipy.optimize import least_squares
from qualified_closure_v1.policy import summarize
from qualified_execution_v1.contact_audit import restored
from qualified_execution_v1.environment import state
from qualified_task_v1.integrity import fingerprint, unchanged
from cm_geometry import place_robot
from routecheck.clone import clone_robot
from guard_runtime import contact_rows
from contact_policy import forbidden
from self_geometry import intersections

SIDES = ('right', 'left')
PARTS = ('coupler', 'spring_link', 'follower')
SAMPLE_COUNT = 81
CONNECT_TOLERANCE_M = 1e-7
PARALLEL_TOLERANCE_RAD = 1e-6
MAX_SOLVER_EVALUATIONS = 200


def linkage(model, side):
    follower, coupler = (model.body(f'{side}_{name}').id for name in ('follower', 'coupler'))
    matches = [i for i in range(model.neq)
               if model.eq_type[i] == mujoco.mjtEq.mjEQ_CONNECT
               and model.eq_obj1id[i] == follower and model.eq_obj2id[i] == coupler]
    if len(matches) != 1:
        raise ValueError('Unsupported gripper connect constraints')
    ids = [model.joint(f'{side}_{name}_joint').id for name in PARTS]
    return dict(eq=matches[0], ids=ids, addresses=model.jnt_qposadr[ids],
                bounds=model.jnt_range[ids].copy())


def residual(model, data, *, info, values):
    data.qpos[info['addresses']] = values
    mujoco.mj_kinematics(model, data)
    eq = info['eq']
    left, right = int(model.eq_obj1id[eq]), int(model.eq_obj2id[eq])
    a = data.xpos[left] + data.xmat[left].reshape(3, 3) @ model.eq_data[eq, :3]
    b = data.xpos[right] + data.xmat[right].reshape(3, 3) @ model.eq_data[eq, 3:6]
    return np.r_[a - b, values[1] + values[2]]


def solve_side(model, data, *, side, angle):
    info = linkage(model, side)
    data.joint(f'{side}_driver_joint').qpos[0] = angle
    limits = info['bounds']
    initial = np.clip([-angle, angle, -angle], limits[:, 0], limits[:, 1])
    solution = least_squares(lambda x: residual(model, data, info=info, values=x),
                            initial, bounds=(limits[:, 0], limits[:, 1]),
                            ftol=1e-12, xtol=1e-12, gtol=1e-12,
                            max_nfev=MAX_SOLVER_EVALUATIONS)
    delta = residual(model, data, info=info, values=solution.x)
    valid = bool(solution.success and np.isfinite(delta).all()
                 and np.max(np.abs(delta[:3])) <= CONNECT_TOLERANCE_M
                 and abs(delta[3]) <= PARALLEL_TOLERANCE_RAD)
    return dict(valid=valid, joints=solution.x.tolist(), connect_error_m=float(np.max(np.abs(delta[:3]))),
                parallel_error_rad=float(abs(delta[3])), evaluations=int(solution.nfev))


def collisions(model, data, source):
    environment = [r for r in contact_rows(model, data) if forbidden(r, source)]
    return environment + intersections(model, data)


def sample(model, values, *, angle, source):
    data = restored(model, values)
    solved = {side: solve_side(model, data, side=side, angle=angle) for side in SIDES}
    mujoco.mj_forward(model, data)
    return dict(angle_rad=float(angle), valid=all(r['valid'] for r in solved.values()),
                linkage=solved, contacts=collisions(model, data, source))


def sweep(env, item, *, command, sample_count=SAMPLE_COUNT):
    if sample_count < 2:
        raise ValueError('Closure sweep needs both endpoints')
    command = np.asarray(command, dtype=float)
    if command.shape != (6,) or not np.isfinite(command).all():
        raise ValueError('Finite six-joint command required')
    before = fingerprint(env)
    model = env.mj_model
    data = restored(model, state(env))
    place_robot(clone_robot(env.robot), env, data, q=command)
    values = state(SimpleNamespace(mj_model=model, mj_data=data))
    driver = model.joint('right_driver_joint').id
    low, high = model.jnt_range[driver]
    left = model.joint('left_driver_joint').id
    np.testing.assert_array_equal(model.jnt_range[left], [low, high])
    rows = [sample(model, values, angle=float(a), source=item['source'])
            for a in np.linspace(low, high, sample_count)]
    result = summarize(rows, expected_count=sample_count)
    result.update(rows=rows, isolation=unchanged(before, fingerprint(env)),
                  method='nominal_parallel_pad_linkage_sweep', command=command.tolist(),
                  angle_range_rad=[float(low), float(high)], integration_steps=0,
                  historical_terminal_fingers_used=False)
    return result
