"""终点先筛：只为抓取与释放均合格的姿态/分支搜索整段路径。"""
from itertools import product
import numpy as np
import mujoco
import spatialmath as sm
from cm_pose import poses
from routecheck.clone import clone_robot
from stability.prepose import inverse
from cm_geometry import sample
from route_geometry import groups,clearance
from goal_geometry import geometry,targets

CONFIGS=tuple(product((1,-1),repeat=3))


def inspect(flow, pose, *, config, item):
    robot=clone_robot(flow.robot)
    q=inverse(robot,pose,reference=flow.q1,config=config)
    if len(q)!=6:
        return dict(ok=False,reason='ik_failure')
    error=float(np.max(np.abs(robot.fkine(q).A-pose.A)))
    assert error<1e-6
    data=mujoco.MjData(flow.env.mj_model)
    data.qpos[:]=flow.env.mj_data.qpos
    result=sample(robot,flow.env,data,value=q,ignore=(item['source'],item['destination']))
    if result['ok']:
        result=clearance(flow.env.mj_model,data,groups(flow.env.mj_model,item['destination']))
    return dict(result,q=q.tolist(),fk_error=error)


def enumerate_goals(flow, *, item):
    dimensions=geometry(flow,item)
    rows,grasps=[],[]
    for pose in poses(flow.T_wo):
        for config in CONFIGS:
            grasp=inspect(flow,pose['pose'],config=config,item=item)
            key=pose['id']+'|'+','.join(map(str,config))
            grasps.append(dict(id=key,pose=pose['id'],config=list(config),**grasp))
            if not grasp['ok']:
                continue
            rows.extend(release_rows(flow,pose,config=config,item=item,dimensions=dimensions,key=key))
    return dict(geometry=dimensions,grasps=grasps,goals=rows,
                passing=sum(r['ok'] for r in rows),grasp_combinations=len(grasps))


def release_rows(flow, pose, *, config, item, dimensions, key):
    rows=[]
    for target in targets(pose['pose'],dimensions):
        release=sm.SE3.Rt(pose['pose'].R,target['target'])
        result=inspect(flow,release,config=config,item=item)
        rows.append(dict(target,id=key+'|'+target['id'],pose=pose['id'],config=list(config),**result))
    return rows
