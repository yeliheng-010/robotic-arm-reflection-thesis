"""复用原机器人保护，逐样本同步持物体积与原支撑退出状态。"""
import numpy as np
import mujoco
import route_geometry
from ot_volume import body_pose,collisions
from ot_volume_v2 import place
from support import Guard

POSE_ATOL=1e-12


class Scene:
    def __init__(self, env, *, item, grasp):
        self.env,self.item,self.grasp=env,item,grasp
        self.data=mujoco.MjData(env.mj_model)
        self.data.qpos[:]=env.mj_data.qpos
        self.initial=body_pose(env.mj_model,env.mj_data,item['source'])
        self.guard=Guard(collisions(env.mj_model,env.mj_data,item['source']))
        self.pairs=route_geometry.groups(env.mj_model,item['destination'])
        self.previous_z=float(grasp.t[2])
        self.support_samples=[]

    def rising(self, tcp, phase):
        answer=phase=='lift' and np.allclose(tcp.R,self.grasp.R,atol=POSE_ATOL,rtol=0)
        answer=answer and np.allclose(tcp.t[:2],self.grasp.t[:2],atol=POSE_ATOL,rtol=0)
        answer=answer and tcp.t[2]>=self.previous_z-POSE_ATOL
        self.previous_z=float(tcp.t[2])
        return bool(answer)

    def sample(self, robot, value, *, phase):
        tcp=robot.fkine(value) if isinstance(value,np.ndarray) else value
        model=self.env.mj_model
        place(model,self.data,source=self.item['source'],initial=self.initial,grasp=self.grasp,release=tcp)
        result=route_geometry.sample(robot,self.env,self.data,value=value,
            ignore=(self.item['source'],self.item['destination']))
        if result['ok']:
            result=route_geometry.clearance(model,self.data,self.pairs)
        held=collisions(model,self.data,self.item['source'])
        rejected=self.guard.check(held,rising=self.rising(tcp,phase))
        if held and not rejected:
            self.support_samples.append(dict(z=float(tcp.t[2]),contacts=held))
        if result['ok'] and rejected:
            result=dict(ok=False,reason='held_object_collision',contacts=rejected)
        return result


def inspect(robot, env, segments, *, item, grasp):
    scene=Scene(env,item=item,grasp=grasp)
    count=0
    for phase,planner,duration in segments:
        for instant in np.linspace(0.,duration,route_geometry.SAMPLES):
            result=scene.sample(robot,planner.interpolate(float(instant)),phase=phase)
            count+=1
            if not result['ok']:
                return dict(feasible=False,samples=count,phase=phase,time=float(instant),
                    failure=result,support_escape=scene.support_samples)
    return dict(feasible=True,samples=count,phase=None,time=None,failure=None,
        support_escape=scene.support_samples)
