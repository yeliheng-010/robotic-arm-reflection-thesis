"""读取编译参数及控制默认值，不执行控制器。"""
import inspect
import mujoco
import numpy as np
import grasp_process as grasp
from qualified_execution_v1.runtime import native_flow

SIDES = ('right', 'left')
PARTS = ('driver', 'coupler', 'spring_link', 'follower')
CLOSE_METHOD = grasp.GraspFlow.close_gripper


def joint_rows(model):
    rows = []
    for side in SIDES:
        for part in PARTS:
            name = f'{side}_{part}_joint'
            index = model.joint(name).id
            qadr, dof = int(model.jnt_qposadr[index]), int(model.jnt_dofadr[index])
            rows.append(dict(name=name, id=index, qpos_address=qadr, dof_address=dof,
                range=model.jnt_range[index].tolist(), limited=bool(model.jnt_limited[index]),
                stiffness=float(model.jnt_stiffness[index]), spring_reference=float(model.qpos_spring[qadr]),
                damping=float(model.dof_damping[dof]), armature=float(model.dof_armature[dof])))
    return rows


def equality_rows(model):
    rows = []
    for index in range(model.neq):
        kind = int(model.eq_type[index])
        if kind not in (int(mujoco.mjtEq.mjEQ_CONNECT), int(mujoco.mjtEq.mjEQ_JOINT)):
            continue
        accessor = model.body if kind == int(mujoco.mjtEq.mjEQ_CONNECT) else model.joint
        ids = [int(model.eq_obj1id[index]), int(model.eq_obj2id[index])]
        names = [accessor(i).name if i >= 0 else None for i in ids]
        if not any(name and name.startswith(('right_', 'left_')) for name in names):
            continue
        rows.append(dict(id=index, type=kind, names=names, active=bool(model.eq_active0[index]),
                         data=model.eq_data[index].tolist()))
    return rows


def actuator_row(model):
    aid = model.actuator('fingers_actuator').id
    assert aid == model.nu - 1
    assert model.actuator_trntype[aid] == mujoco.mjtTrn.mjTRN_TENDON
    tid = int(model.actuator_trnid[aid, 0])
    wraps = range(int(model.tendon_adr[tid]), int(model.tendon_adr[tid] + model.tendon_num[tid]))
    entries = [dict(type=int(model.wrap_type[i]), joint=model.joint(int(model.wrap_objid[i])).name,
                    coefficient=float(model.wrap_prm[i])) for i in wraps]
    return dict(id=aid, tendon=model.tendon(tid).name, wraps=entries, gear=model.actuator_gear[aid].tolist(),
        gain_type=int(model.actuator_gaintype[aid]), bias_type=int(model.actuator_biastype[aid]),
        dynamics_type=int(model.actuator_dyntype[aid]),
        ctrlrange=model.actuator_ctrlrange[aid].tolist(), forcerange=model.actuator_forcerange[aid].tolist(),
        ctrllimited=bool(model.actuator_ctrllimited[aid]), forcelimited=bool(model.actuator_forcelimited[aid]),
        gainprm=model.actuator_gainprm[aid].tolist(), biasprm=model.actuator_biasprm[aid].tolist())


def controller(env, plan):
    flow = native_flow(env, plan)
    assert len(flow.action) == env.mj_model.nu
    function = inspect.signature(grasp.close_gripper).parameters
    method = inspect.signature(CLOSE_METHOD).parameters
    loops, delta = int(function['loops'].default), float(function['delta'].default)
    assert loops == method['loops'].default and delta == method['delta'].default
    start = float(flow.action[-1])
    value, controls = start, []
    for _ in range(loops):
        value = min(value + delta, 255.)
        controls.append(value)
    return dict(default_loops=loops, default_delta=delta, initial_command=start,
                first_command=controls[0], last_command=controls[-1], control_commands=controls,
                actual_controller_called=False, assumes_prefix_preserves_gripper_command=True)
