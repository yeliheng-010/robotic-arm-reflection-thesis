"""独立端点核验：FK一致性、碰撞几何与不经AABB筛选的全几何对净空。"""
import numpy as np
import mujoco
import spatialmath as sm
from routecheck.clone import clone_robot
from stability.prepose import inverse
from cm_geometry import place_robot
from guard_runtime import contact_rows
from contact_policy import forbidden
from cm_pose import poses
from cm_planning import RELEASE_OFFSET

CLEARANCE_M = .010


def destination_pairs(model, destination):
    active = (model.geom_contype != 0) | (model.geom_conaffinity != 0)
    roots = model.body_rootid[model.geom_bodyid]
    robot_roots = [model.body(n).id for n in ('ur5e_base','2f85_base')]
    robots = np.flatnonzero(active & np.isin(roots,robot_roots))
    target = np.flatnonzero(active & (roots==model.body(destination).id))
    return [(int(a),int(b)) for a in robots for b in target]


def measure(flow, pose, *, config, item):
    robot = clone_robot(flow.robot)
    q = inverse(robot,pose,reference=flow.q1,config=config)
    assert len(q) == 6, 'All diagnosed release endpoints had IK solutions'
    fk_error = float(np.max(np.abs(robot.fkine(q).A-pose.A)))
    assert fk_error < 1e-6
    model = flow.env.mj_model
    data = mujoco.MjData(model)
    data.qpos[:] = flow.env.mj_data.qpos
    place_robot(robot,flow.env,data,q=q)
    hits = [r for r in contact_rows(model,data) if forbidden(r,item['source'])]
    distances = [(float(mujoco.mj_geomDistance(model,data,a,b,CLEARANCE_M,None)),a,b)
                 for a,b in destination_pairs(model,item['destination'])]
    distance, a, b = min(distances)
    reason = 'collision' if hits else 'destination_clearance' if distance<CLEARANCE_M else None
    return dict(ok=reason is None,reason=reason,fk_max_error=fk_error,contacts=hits,
                distance_m=distance,closest_geoms=[model.geom(a).name or str(a),model.geom(b).name or str(b)],
                closest_bodies=[model.body(model.geom_bodyid[g]).name for g in (a,b)])


def inspect(flow, rows, *, item, parameters):
    options = {r['id']:r['pose'] for r in poses(flow.T_wo)}
    target = flow.env.mj_data.body(item['destination']).xpos.copy()
    target += np.array(parameters['place_offset'])+np.array([0.,0.,RELEASE_OFFSET])
    results = []
    for row in rows:
        release = sm.SE3.Rt(options[row['pose']].R,target)
        measured = measure(flow,release,config=row['config'],item=item)
        assert measured['ok'] == row['release']['ok'] and measured['reason'] == row['release']['reason']
        assert not measured['ok']
        if measured['reason']=='collision':
            assert any(item['destination'] in r['roots'] for r in measured['contacts'])
        results.append(dict(pose=row['pose'],config=row['config'],**measured))
    return results
