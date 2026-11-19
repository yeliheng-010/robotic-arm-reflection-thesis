"""副本上的机械臂几何检查；夹爪和物体动态仍由完整执行验证。"""
import mujoco
import numpy as np
from reflection.sim_sensing import robot_environment_contacts
from routecheck.clone import clone_robot

SAMPLES = 51
DISTANCE_CAP = .5
JOINTS = 6
CONFIG = ('overhead','inline','wrist')


def state(robot,env):
    spec = mujoco.mjtState.mjSTATE_INTEGRATION
    integration = np.empty(mujoco.mj_stateSize(env.mj_model,spec))
    mujoco.mj_getState(env.mj_model,env.mj_data,integration,spec)
    return dict(integration=integration,joints=robot.get_joint(),
                config=[getattr(robot.robot_config,n) for n in CONFIG])


def unchanged(before,after):
    np.testing.assert_array_equal(before['integration'],after['integration'])
    np.testing.assert_array_equal(before['joints'],after['joints'])
    assert before['config']==after['config']


def geometry(env,q):
    model = env.mj_model
    data = mujoco.MjData(model)
    data.qpos[:] = env.mj_data.qpos
    for name,value in zip(env.joint_names,q):
        data.joint(name).qpos[0] = value
    mujoco.mj_forward(model,data)
    pairs = robot_environment_contacts(model,data,ignore=('PurpleCapsule','RedBin'))
    arm_pairs = [list(p) for p in pairs if p[0]=='ur5e_base']
    wrist = model.body('wrist_1_link').id
    geoms = [i for i in range(model.ngeom) if model.geom_bodyid[i]==wrist and
             (model.geom_contype[i] or model.geom_conaffinity[i])]
    divider = model.geom('safety_divider').id
    distances = [mujoco.mj_geomDistance(model,data,g,divider,DISTANCE_CAP,None) for g in geoms]
    return dict(arm_contacts=arm_pairs,wrist_divider_distance=float(min(distances)),
                wrist_xyz=data.body(wrist).xpos.tolist())


def sample(robot,env,pose):
    q = robot.ikine(pose)
    if len(q)!=JOINTS:
        return dict(ik=False)
    robot.q0 = q.copy()
    error = float(np.max(np.abs(robot.fkine(q).A-pose.A)))
    assert error<1e-6, 'Inverse/forward kinematics mismatch'
    return dict(ik=True,q=q.tolist(),fk_max_error=error,**geometry(env,q))


def inspect(robot,env,planned,*,yaw):
    clone = clone_robot(robot)
    rows = []
    names = ('lift','transport','descent')
    for phase,planner,duration in zip(names,planned['planners'],planned['durations'][1:]):
        for t in np.linspace(0,float(duration),SAMPLES):
            pose = planner.interpolate(float(t))
            rows.append(dict(phase=phase,time=float(t),xyz=pose.t.tolist(),**sample(clone,env,pose)))
    endpoint = rows[-1]
    return dict(yaw_deg=yaw,scope='static_arm_only',samples_per_segment=SAMPLES,rows=rows,
                endpoint=endpoint,ik_failures=sum(not r['ik'] for r in rows),
                collision_samples=sum(bool(r.get('arm_contacts')) for r in rows),
                distance_cap_m=DISTANCE_CAP)
