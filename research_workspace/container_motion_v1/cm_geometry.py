"""在数据副本中同步机械臂和自由夹爪，检查完整路径抽样。"""
import mujoco
import numpy as np
from reflection.sim_sensing import robot_environment_contacts
from manipulator_grasp.utils.mj import set_free_joint_pose

SAMPLES = 51
JOINTS = 6
FK_TOLERANCE = 1e-6


def place_robot(robot, env, data, *, q):
    for name,value in zip(env.joint_names,q):
        data.joint(name).qpos[0] = value
    flange = robot.fkine(q)*robot._tool.inv()
    set_free_joint_pose(env.mj_model,data,'2f85',flange)
    mujoco.mj_forward(env.mj_model,data)
    np.testing.assert_allclose(flange.t,data.body('2f85_base').xpos,atol=1e-8,rtol=0)


def sample(robot, env, data, *, value, ignore):
    if isinstance(value,np.ndarray):
        q = value
        robot.set_joint(q)
    else:
        q = robot.ikine(value)
        if len(q)!=JOINTS:
            return dict(ok=False,reason='ik_failure')
        assert np.max(np.abs(robot.fkine(q).A-value.A))<FK_TOLERANCE
        robot.q0 = q.copy()
    place_robot(robot,env,data,q=q)
    hits = robot_environment_contacts(env.mj_model,data,ignore=ignore)
    return dict(ok=not hits,reason='collision' if hits else None,contacts=[list(x) for x in hits])


def inspect(robot, env, segments, *, ignore):
    data = mujoco.MjData(env.mj_model)
    data.qpos[:] = env.mj_data.qpos
    count = 0
    for phase,planner,duration in segments:
        for time in np.linspace(0,float(duration),SAMPLES):
            result = sample(robot,env,data,value=planner.interpolate(float(time)),ignore=ignore)
            count += 1
            if not result['ok']:
                return dict(feasible=False,samples=count,phase=phase,time=float(time),failure=result)
    return dict(feasible=True,samples=count,phase=None,time=None,failure=None)
