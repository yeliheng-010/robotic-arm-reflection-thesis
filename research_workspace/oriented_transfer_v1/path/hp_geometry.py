"""持物路径每样本重建源物体姿态，保持原机器人安全检查。"""
import numpy as np
import mujoco
import route_geometry
from ot_volume import body_pose,collisions
from ot_volume_v2 import place
from hp_policy import allowed_initial


def inspect(robot, env, segments, *, item, grasp):
    model=env.mj_model
    data=mujoco.MjData(model)
    data.qpos[:]=env.mj_data.qpos
    initial=body_pose(model,env.mj_data,item['source'])
    baseline=collisions(model,env.mj_data,item['source'])
    pairs=route_geometry.groups(model,item['destination'])
    count=0
    for phase,planner,duration in segments:
        for instant in np.linspace(0.,duration,route_geometry.SAMPLES):
            value=planner.interpolate(float(instant))
            tcp=robot.fkine(value) if isinstance(value,np.ndarray) else value
            place(model,data,source=item['source'],initial=initial,grasp=grasp,release=tcp)
            result=route_geometry.sample(robot,env,data,value=value,ignore=(item['source'],item['destination']))
            if result['ok']:
                result=route_geometry.clearance(model,data,pairs)
            held=collisions(model,data,item['source'])
            rejected=[r for r in held if not allowed_initial(r,baseline,first_sample=count==0 and phase=='lift')]
            if result['ok'] and rejected:
                result=dict(ok=False,reason='held_object_collision',contacts=rejected)
            count+=1
            if not result['ok']:
                return dict(feasible=False,samples=count,phase=phase,time=float(instant),failure=result)
    return dict(feasible=True,samples=count,phase=None,time=None,failure=None)
