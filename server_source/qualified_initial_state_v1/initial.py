"""构造一次合成闭合起点；不积分、不重新求IK。"""
import mujoco
import numpy as np
from cm_geometry import place_robot
from routecheck.clone import clone_robot
from qualified_closure_reachability_v1.parameters import joint_rows, actuator_row, equality_rows
from qualified_closure_dynamics_v1.capture import state, write_npz
from qualified_closure_dynamics_v1.protocol import save, require

CONNECT_TOLERANCE = 1e-7
DRIVER_TOLERANCE = 1e-7
ATTACH_TOLERANCE = 1e-6


def validate_model(env, expected):
    model = env.mj_model
    require(model.nu == 7 and model.na == 0, 'Unexpected actuator state')
    require(joint_rows(model) == expected['joints'], 'Finger parameters changed')
    require(actuator_row(model) == expected['actuator'], 'Gripper actuator changed')
    require(equality_rows(model) == expected['equalities'], 'Finger equalities changed')
    for index, name in enumerate(env.joint_names):
        require(model.actuator_trntype[index] == mujoco.mjtTrn.mjTRN_JOINT,
                'Unexpected arm actuator transmission')
        require(model.actuator_trnid[index, 0] == model.joint(name).id, 'Arm control order')
    for name in dir(mujoco):
        if name.startswith('get_mjcb_'):
            require(getattr(mujoco, name)() is None, 'Unexpected callback: ' + name)


def equality_check(model, data):
    rows = []
    for index in range(model.neq):
        if not data.eq_active[index]:
            continue
        selected = (data.efc_type == mujoco.mjtConstraint.mjCNSTR_EQUALITY) & (data.efc_id == index)
        residual = data.efc_pos[selected]
        kind = int(model.eq_type[index])
        tolerance = CONNECT_TOLERANCE if kind == int(mujoco.mjtEq.mjEQ_CONNECT) else DRIVER_TOLERANCE
        if kind == int(mujoco.mjtEq.mjEQ_WELD):
            tolerance = ATTACH_TOLERANCE
        rows.append(dict(id=index, name=model.equality(index).name, type=kind,
                         residual=residual.tolist(), tolerance=tolerance,
                         passed=bool(len(residual) and np.isfinite(residual).all()
                                     and np.max(np.abs(residual)) <= tolerance)))
    attach = model.equality('attach').id
    require(bool(data.eq_active[attach]), 'Attach equality inactive')
    return rows


def prepare(env, inputs, *, expected, folder):
    model, data = env.mj_model, env.mj_data
    validate_model(env, expected)
    before = state(model, data)
    original_qpos = data.qpos.copy()
    command = np.asarray(inputs['command'])
    require(command.shape == (6,) and np.isfinite(command).all(), 'Invalid command')
    place_robot(clone_robot(env.robot), env, data, q=command)
    for name in ('qvel', 'qacc_warmstart', 'qfrc_applied', 'xfrc_applied'):
        getattr(data, name)[:] = 0
    data.ctrl[:] = np.r_[command, 0.0]
    mujoco.mj_forward(model, data)
    joints = joint_rows(model)
    for row in joints:
        require(data.qpos[row['qpos_address']] == original_qpos[row['qpos_address']], 'Finger moved')
    checks = equality_check(model, data)
    bounds = [bool(row['range'][0] <= data.qpos[row['qpos_address']] <= row['range'][1]) for row in joints]
    allowed = {int(model.jnt_qposadr[model.joint(n).id]) for n in env.joint_names}
    free = int(model.jnt_qposadr[model.joint('2f85').id])
    allowed.update(range(free, free + 7))
    changed = np.flatnonzero(original_qpos != data.qpos).tolist()
    require(set(changed) <= allowed, 'Scene qpos changed')
    write_npz(folder / 'initial_transform.npz', dict(before=before, after=state(model, data)))
    save(folder / 'initial.json', dict(kind='synthetic_not_post_approach', changed_qpos=changed,
         equalities=checks, finger_limits=bounds, command=command.tolist(),
         cleared=['qvel', 'qacc_warmstart', 'qfrc_applied', 'xfrc_applied']))
    return [] if all(bounds) and all(row['passed'] for row in checks) else ['initial_constraints']
