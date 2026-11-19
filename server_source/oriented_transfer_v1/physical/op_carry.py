"""执行前再次核验当前真实持物状态，不绕过原机器人和释放保护。"""
from inspect import signature
import numpy as np
import spatialmath as sm
import grasp_process as grasp
from reflection.monitors import abort,ErrorType
from routecheck.clone import clone_robot
from rh_runtime import robot_context
from live_motion import plan_values
from hv_geometry import inspect
from commands import build
from op_common import save


def factory(original, trace, *, session):
    def move(*args,**kwargs):
        values=signature(original).bind(*args,**kwargs)
        values.apply_defaults()
        v=values.arguments
        selected=trace['selected']['held_selection']
        pose=sm.SE3(np.array(selected['prefix']['pose']))
        np.testing.assert_allclose(pose.A,v['T_start'].A,atol=1e-6,rtol=0)
        paths,times,poses=build(selected,v['time4'])
        segments=[('lift' if i==0 else 'held_joint_'+str(i-1),p,t)
            for i,(p,t) in enumerate(zip(paths,times))]
        context=robot_context(v['robot'],v['env'])
        checked=inspect(clone_robot(v['robot']),v['env'],segments,item=session.case['item'],grasp=pose)
        save(session.folder/'live_held_check.json',dict(context=context,grasp=pose.A.tolist(),
            legs=plan_values(segments),result=checked,selected=selected))
        if not checked['feasible']:
            abort(ErrorType.COLLISION,'Current held-object path rejected',
                route_planning_rejected=True,guard_kind='live_held_object_path')
        result=grasp._run_planners(v['robot'],v['env'],paths,[0.,*times],v['action'],v['dt'])
        return result,poses
    return move
