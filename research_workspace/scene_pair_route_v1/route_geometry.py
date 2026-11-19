"""数据副本内完整路径检查，保留目标箱理想几何净空。"""
import mujoco
import numpy as np
from cm_geometry import sample

CLEARANCE_M = .010
SAMPLES = 51
ROBOTS = ('ur5e_base', '2f85_base')


def groups(model, destination):
    roots = model.body_rootid[model.geom_bodyid]
    active = (model.geom_contype != 0) | (model.geom_conaffinity != 0)
    robot_ids = [model.body(name).id for name in ROBOTS]
    return (np.flatnonzero(active & np.isin(roots, robot_ids)),
            np.flatnonzero(active & (roots == model.body(destination).id)))


def bounds(model, data):
    rotation = data.geom_xmat.reshape(-1, 3, 3)
    centers = data.geom_xpos + np.einsum('ijk,ik->ij', rotation, model.geom_aabb[:, :3])
    extents = np.einsum('ijk,ik->ij', np.abs(rotation), model.geom_aabb[:, 3:])
    return centers-extents, centers+extents


def clearance(model, data, pairs):
    robots, obstacles = pairs
    low, high = bounds(model, data)
    gap = np.maximum(np.maximum(low[robots, None]-high[obstacles], low[obstacles]-high[robots, None]), 0)
    nearby = np.argwhere(np.linalg.norm(gap, axis=2) < CLEARANCE_M)
    for a, b in nearby:
        gid, other = int(robots[a]), int(obstacles[b])
        distance = mujoco.mj_geomDistance(model, data, gid, other, CLEARANCE_M, None)
        if distance < CLEARANCE_M:
            return dict(ok=False, reason='destination_clearance', distance=float(distance),
                        geoms=[gid, other], required=CLEARANCE_M)
    return dict(ok=True)


def inspect(robot, env, segments, *, item):
    data = mujoco.MjData(env.mj_model)
    data.qpos[:] = env.mj_data.qpos
    pairs = groups(env.mj_model, item['destination'])
    count = 0
    for phase, planner, duration in segments:
        for instant in np.linspace(0, float(duration), SAMPLES):
            result = sample(robot, env, data, value=planner.interpolate(float(instant)),
                            ignore=(item['source'], item['destination']))
            count += 1
            if result['ok']:
                result = clearance(env.mj_model, data, pairs)
            if not result['ok']:
                return dict(feasible=False, samples=count, phase=phase, time=float(instant), failure=result)
    return dict(feasible=True, samples=count, phase=None, time=None, failure=None)
