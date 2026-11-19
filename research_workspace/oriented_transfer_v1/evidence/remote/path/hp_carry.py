"""先保留原抬升，再检查连续关节搬运；分支不能跳变。"""
import numpy as np
import spatialmath as sm
from routecheck.clone import clone_robot
from waypoint_paths import cartesian
from stability.prepose import inverse
from bounded_ik import limits,representatives
from js_geometry import option
from rh_planner import planners
from hp_geometry import inspect


def joint_options(robot, flow, goal, *, minimum, lift):
    start=robot.get_joint().tolist()
    bounds=limits(flow.env.mj_model)
    target=representatives(goal['q'],start,bounds).tolist()
    yield dict(option([start,target],minimum),id='direct_joint')
    release=sm.SE3(np.array(goal['release']))
    above=sm.SE3.Trans(0.,0.,lift)*release
    q=inverse(clone_robot(robot),above,reference=np.array(target),config=goal['config'])
    if len(q)==6:
        yield dict(option([start,q.tolist(),target],minimum),id='via_above_release')


def carry(flow, prefix, checker, *, goals, parameters, item, ledger, maximum, record):
    grasp=sm.SE3(np.array(prefix['pose']))
    minimum,lift=parameters['time_scale'],parameters['lift_height']
    elevated=sm.SE3.Trans(0.,0.,lift)*grasp
    lift_segments=[('lift',cartesian(grasp,elevated,minimum),minimum)]
    lifted=clone_robot(checker)
    lift_check=inspect(lifted,flow.env,lift_segments,item=item,grasp=grasp)
    if not lift_check['feasible']:
        row=dict(prefix_id=prefix['id'],stage='lift',**lift_check)
        ledger.append(row)
        record('carry',row)
        return None
    for goal in goals:
        for route in joint_options(lifted,flow,goal,minimum=minimum,lift=lift):
            if len(ledger)>=maximum:
                return None
            segments=[('held_joint_'+str(i),p,t) for i,(p,t) in enumerate(zip(planners(route),route['durations']))]
            check=inspect(clone_robot(lifted),flow.env,segments,item=item,grasp=grasp)
            row=dict(prefix_id=prefix['id'],goal=goal,route=route,lift=lift,stage='transport',**check)
            ledger.append(row)
            record('carry',row)
            if check['feasible']:
                return dict(prefix=prefix,goal=goal,route=route,lift=lift,lift_check=lift_check,carry_check=check)
    return None
