"""固定预算下搜索抓取前缀和带持物体积的连续关节运输。"""
import numpy as np
import grasp_process as grasp
import waypoint_search
from waypoint_paths import collect,corridor
from waypoint_policy import ROUTES
from route_geometry import inspect
from routecheck.clone import clone_robot
from routecheck.static import state,unchanged
from jg_geometry import Advisor
from jg_paths import context
from hp_carry import carry

MAX_PREFIX=256
MAX_CARRY=512


def eligible(row, goals):
    return [g for g in goals if g['pose']==row['pose_name'] and g['source_config']==row['config']]


def explore(flow, *, item, parameters, goals, record):
    prefixes,transports,events=[],[],[]
    advisor=Advisor(flow,item=item,parameters=parameters,record=events.append)
    edges=corridor(flow.env,item['destination'])
    for option in waypoint_search.options(flow):
        row=waypoint_search.prepose(flow,option)
        row['pose_name']=option['id'].rsplit('_safe',1)[0] if option['rise'] is None else option['id'].rsplit('_',2)[0]
        targets=eligible(row,goals) if len(row['q1'])==6 else []
        if not targets:
            continue
        row=advisor.choose(row)
        if row is None:
            continue
        for route in ROUTES:
            if len(prefixes)>=MAX_PREFIX or len(transports)>=MAX_CARRY:
                return dict(selected=None,status='path_budget_exhausted',prefixes=prefixes,carry=transports,events=events)
            proxy=waypoint_search.proxy(flow,row)
            proxy.joint_option=row.get('joint_option')
            segments=collect(proxy,grasp.move_to_grasp_pose,parameters=parameters,phase='prefix',route=route,edges=edges)
            checker=clone_robot(flow.robot)
            check=inspect(checker,flow.env,segments,item=item)
            current=dict(row,id=row['id']+'_'+route,approach_route=route,**check)
            prefixes.append(current)
            record('prefix',current)
            if check['feasible']:
                selected=carry(flow,current,checker,goals=targets,parameters=parameters,item=item,
                    ledger=transports,maximum=MAX_CARRY,record=record)
                if selected:
                    return dict(selected=selected,status='selected',prefixes=prefixes,carry=transports,events=events)
            if not check['feasible'] and check['phase']=='pregrasp':
                break
    return dict(selected=None,status='registered_paths_exhausted',prefixes=prefixes,carry=transports,events=events)


def choose(flow, *, item, parameters, goals, record):
    before=state(flow.robot,flow.env)
    with context():
        result=explore(flow,item=item,parameters=parameters,goals=goals,record=record)
    unchanged(before,state(flow.robot,flow.env))
    return dict(result,unchanged=True,physical_attempts=0,model_calls=0,
        limitations=['discrete_51_samples','rigid_grasp_assumed','open_gripper_geometry','tracking_not_predicted'])
