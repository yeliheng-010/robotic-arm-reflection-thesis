"""独立放置朝向的有预算端点检查，只输出私有工程证据。"""
from itertools import product
import numpy as np
import mujoco
import spatialmath as sm
import goal_endpoints
from goal_geometry import geometry
from goal_policy import GRID,BOTTOM_GAPS_M,EDGE_MARGIN_M
from route_geometry import clearance,groups
from routecheck.clone import clone_robot
from stability.prepose import inverse
from ot_geometry import release_target,moved
from ot_volume import body_pose,place,collisions,corners

YAWS=(0.,45.,-45.,90.,-90.,135.,-135.,180.)
MAX_ENDPOINTS=4096


def measure(flow, grasp, release, *, item, config):
    robot=clone_robot(flow.robot)
    q=inverse(robot,release,reference=flow.q1,config=config)
    if len(q)!=6:
        return dict(ok=False,reason='ik_failure')
    np.testing.assert_allclose(release.A,robot.fkine(q).A,atol=1e-6,rtol=0)
    model=flow.env.mj_model
    data=mujoco.MjData(model)
    data.qpos[:]=flow.env.mj_data.qpos
    initial=body_pose(model,flow.env.mj_data,item['source'])
    place(model,data,source=item['source'],initial=initial,grasp=grasp,release=release)
    check=goal_endpoints.sample(robot,flow.env,data,value=q,ignore=(item['source'],item['destination']))
    if check['ok']:
        check=clearance(model,data,groups(model,item['destination']))
    held=collisions(model,data,item['source'])
    if check['ok'] and held:
        check=dict(ok=False,reason='held_object_collision',contacts=held)
    predicted=moved(corners(model,flow.env.mj_data,item['source']),grasp,release)
    np.testing.assert_allclose(predicted,corners(model,data,item['source']),atol=1e-8,rtol=0)
    return dict(check,q=q.tolist(),release=release.A.tolist(),held_pose=body_pose(model,data,item['source']).A.tolist())


def candidates(grasps, poses, *, points, dimensions):
    for grid,gap,yaw,row in product(GRID,BOTTOM_GAPS_M,YAWS,grasps):
        grasp=poses[row['pose']]
        rotation=sm.SO3.Rz(yaw,unit='deg').R@grasp.R
        try:
            release=release_target(grasp,rotation,points=points,dimensions=dimensions,grid=grid,gap=gap)
        except ValueError as error:
            assert str(error)=='Rotated volume does not fit registered margin'
            continue
        yield dict(grasp=row,yaw=yaw,grid=list(grid),gap=gap,release=release)


def inspect(flow, *, item, grasps, poses, record):
    dimensions=geometry(flow,item)
    points=corners(flow.env.mj_model,flow.env.mj_data,item['source'])
    rows=[]
    for candidate in candidates(grasps,poses,points=points,dimensions=dimensions):
        if len(rows)>=MAX_ENDPOINTS:
            return rows,'endpoint_budget_exhausted'
        row=candidate['grasp']
        result=measure(flow,poses[row['pose']],candidate['release'],item=item,config=row['config'])
        current=dict(index=len(rows),grasp=row['id'],pose=row['pose'],config=row['config'],
            yaw=candidate['yaw'],grid=candidate['grid'],gap=candidate['gap'],**result)
        rows.append(current)
        record(current)
    return rows,'registered_endpoints_exhausted'
