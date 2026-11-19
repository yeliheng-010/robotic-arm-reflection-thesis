"""新增机械臂自碰撞检查；保留原环境检查、夹爪内部接触和目标箱净空。"""
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
import cm_geometry
import route_geometry
import goal_endpoints

ARM = 'ur5e_base'
GRIPPER = '2f85_base'


def forbidden(roots, distance):
    return distance < 0 and ARM in roots and all(r in (ARM, GRIPPER) for r in roots)


def intersections(model, data):
    rows = []
    for contact in data.contact[:data.ncon]:
        gids = (int(contact.geom1), int(contact.geom2))
        bids = [int(model.geom_bodyid[g]) for g in gids]
        roots = [model.body(model.body_rootid[b]).name for b in bids]
        if forbidden(roots, float(contact.dist)):
            rows.append(dict(geoms=list(gids), bodies=[model.body(b).name for b in bids],
                             roots=roots, distance=float(contact.dist)))
    return rows


def wrapper(original):
    def checked(robot, env, data, *, value, ignore):
        result = original(robot, env, data, value=value, ignore=ignore)
        if not result['ok']:
            return result
        hits = intersections(env.mj_model, data)
        if hits:
            return dict(ok=False, reason='robot_self_collision', contacts=hits)
        return result
    return checked


@contextmanager
def context():
    original = cm_geometry.sample
    assert route_geometry.sample is original and goal_endpoints.sample is original
    with ExitStack() as stack:
        for module in (cm_geometry, route_geometry, goal_endpoints):
            stack.enter_context(patch.object(module, 'sample', wrapper(original)))
        yield
