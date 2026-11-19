"""仅在数据副本中移动自由物体并检查其真实碰撞几何。"""
from itertools import product
import numpy as np
import mujoco
import spatialmath as sm

SIGNS=np.array(list(product((-1.,1.),repeat=3)))
GRIPPER='2f85_base'


def body_pose(model, data, source):
    body=data.body(source)
    return sm.SE3.Rt(body.xmat.reshape(3,3),body.xpos.copy())


def place(model, data, *, source, initial, grasp, release):
    bid=model.body(source).id
    jid=int(model.body_jntadr[bid])
    assert model.body_parentid[bid]==0 and model.body_jntnum[bid]==1
    assert model.jnt_type[jid]==mujoco.mjtJoint.mjJNT_FREE
    value=release*grasp.inv()*initial
    adr=int(model.jnt_qposadr[jid])
    quat=np.empty(4)
    mujoco.mju_mat2Quat(quat,np.asarray(value.R).flatten())
    data.qpos[adr:adr+7]=np.r_[value.t,quat]
    mujoco.mj_forward(model,data)


def collisions(model, data, source):
    rows=[]
    for c in data.contact[:data.ncon]:
        ids=[int(c.geom1),int(c.geom2)]
        roots=[model.body(model.body_rootid[model.geom_bodyid[g]]).name for g in ids]
        if source not in roots or c.dist>=0:
            continue
        other=roots[1] if roots[0]==source else roots[0]
        if other in (source,GRIPPER):
            continue
        rows.append(dict(geoms=ids,roots=roots,distance=float(c.dist)))
    return rows


def corners(model, data, source):
    bid=model.body(source).id
    active=(model.geom_contype!=0)|(model.geom_conaffinity!=0)
    ids=np.flatnonzero(active&(model.body_rootid[model.geom_bodyid]==bid))
    if not len(ids):
        raise ValueError('No active source geometry')
    rows=[]
    for gid in ids:
        local=model.geom_aabb[gid,:3]+SIGNS*model.geom_aabb[gid,3:]
        rotation=data.geom_xmat[gid].reshape(3,3)
        rows.extend(local@rotation.T+data.geom_xpos[gid])
    return np.array(rows)
