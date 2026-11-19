"""读取仿真数据，不推进仿真、不修改模型或控制器。"""
import mujoco
import numpy as np
from reflection.sim_sensing import pad_contacts, ROBOT_ROOT_BODIES

PAD_NAMES = ('left_pad1', 'left_pad2', 'right_pad1', 'right_pad2')


def geom_info(model, data, gid):
    rotation = data.geom_xmat[gid].reshape(3, 3)
    center = data.geom_xpos[gid] + rotation @ model.geom_aabb[gid, :3]
    extent = np.abs(rotation) @ model.geom_aabb[gid, 3:]
    return dict(name=model.geom(gid).name, center=data.geom_xpos[gid].tolist(),
                low=(center-extent).tolist(), high=(center+extent).tolist())


def contacts(env, source):
    model, data = env.mj_model, env.mj_data
    rows = []
    for index, contact in enumerate(data.contact[:data.ncon]):
        gids = (contact.geom1, contact.geom2)
        roots = [model.body(model.body_rootid[model.geom_bodyid[g]]).name for g in gids]
        if source not in roots and not set(roots).intersection(ROBOT_ROOT_BODIES):
            continue
        force = np.zeros(6)
        mujoco.mj_contactForce(model, data, index, force)
        rows.append(dict(geoms=[model.geom(g).name for g in gids], roots=roots,
                         point=contact.pos.tolist(), distance=float(contact.dist),
                         force=force.tolist()))
    return rows


def pose(env):
    data = env.mj_data
    flange = np.eye(4)
    flange[:3, :3] = data.body('2f85_base').xmat.reshape(3, 3)
    flange[:3, 3] = data.body('2f85_base').xpos
    return flange @ env.robot._tool.A


def sample(env, item):
    model, data = env.mj_model, env.mj_data
    source = item['source']
    bid = model.body(source).id
    touched = {k: sorted(v) for k, v in pad_contacts(model, data).items()}
    return dict(time=float(data.time), source=data.body(source).xpos.tolist(),
                destination=data.body(item['destination']).xpos.tolist(),
                tcp=pose(env).tolist(), command=env.robot.get_cartesian().A.tolist(),
                ctrl=data.ctrl.tolist(), closure=float(data.joint('right_driver_joint').qpos[0]),
                qpos=data.qpos[:6].tolist(), pads=touched,
                pad_geometry=[geom_info(model, data, model.geom(n).id) for n in PAD_NAMES],
                source_geometry=[geom_info(model, data, int(g))
                                 for g in np.flatnonzero(model.geom_bodyid == bid)],
                contacts=contacts(env, source))
