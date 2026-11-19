"""沿用reset构造完整模型，跳过cv_select.scene的500步。"""
from contextlib import contextmanager
from pathlib import Path
import numpy as np
import mujoco
from sd_runtime import context
from sd_scene import apply
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from qualified_closure_dynamics_v1.initial import validate_model
from qualified_scene_candidate_v1.common import PROJECT, CANDIDATE, read, require

ARMS = ('shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
        'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint')


def state(model, data):
    spec = mujoco.mjtState.mjSTATE_INTEGRATION
    values = np.empty(mujoco.mj_stateSize(model, spec))
    mujoco.mj_getState(model, data, values, spec)
    return values


def candidate():
    with np.load(CANDIDATE, allow_pickle=False) as data:
        return data['integration'].copy()


def restore(model, data, values):
    require(values.shape == state(model, data).shape and np.isfinite(values).all(), 'State layout mismatch')
    mujoco.mj_setState(model, data, values, mujoco.mjtState.mjSTATE_INTEGRATION)
    np.testing.assert_array_equal(values, state(model, data))
    mujoco.mj_forward(model, data)
    np.testing.assert_array_equal(values, state(model, data))


def layout(env):
    model = env.mj_model
    parameters = read(PROJECT / 'qualified_closure_reachability_v1/run/parameters.json')
    validate_model(env, parameters)
    for index, name in enumerate(ARMS):
        require(model.joint(name).id == index and model.jnt_qposadr[index] == index, 'Arm layout changed')
    free = model.joint('2f85').id
    require(free == 6 and model.jnt_qposadr[free] == 6, 'Free gripper layout changed')
    joints = [dict(id=i, name=model.joint(i).name, type=int(model.jnt_type[i]),
                   qpos=int(model.jnt_qposadr[i]), dof=int(model.jnt_dofadr[i])) for i in range(model.njnt)]
    return dict(nq=model.nq, nv=model.nv, nu=model.nu, na=model.na, neq=model.neq,
                nbody=model.nbody, ngeom=model.ngeom, joints=joints, state_size=state(model, env.mj_data).size)


@contextmanager
def restored_scene(config):
    with context(config):
        env = UR5GraspEnv(headless=True, model_editor=lambda spec: apply(spec, config))
        try:
            env.reset()
            mapping = layout(env)
            values = candidate()
            restore(env.mj_model, env.mj_data, values)
            env.robot_q = np.array([env.mj_data.joint(n).qpos[0] for n in ARMS])
            env.robot.set_joint(env.robot_q)
            env.robot_T = env.robot.fkine(env.robot_q)
            np.testing.assert_array_equal(values, state(env.mj_model, env.mj_data))
            yield env, mapping
        finally:
            env.close()
