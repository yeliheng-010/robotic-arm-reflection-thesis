"""先终点、后前缀、再运输；有限搜索耗尽不称为全局无解。"""
from itertools import product
import numpy as np
import spatialmath as sm
from cm_planning import context
from cm_pose import poses
from routecheck.clone import clone_robot
from routecheck.static import state,unchanged
from route_geometry import inspect
from waypoint_search import options,prepose,proxy
from waypoint_paths import corridor,collect
from waypoint_policy import ROUTES,LIFTS
from goal_policy import MAX_PREFIX,MAX_CARRY
from goal_endpoints import enumerate_goals


def compatible(option, row, endpoints):
    name=option['id'].rsplit('_safe',1)[0] if option['rise'] is None else option['id'].rsplit('_',2)[0]
    return [r for r in endpoints['goals'] if r['ok'] and r['pose']==name and r['config']==row['config']]


def transport(flow, row, checker, *, goals, parameters, hooks, edges, item, budget):
    rows=[]
    for goal,lift,route in product(goals,LIFTS,ROUTES):
        if len(rows)>=budget:
            return rows
        segments=collect(proxy(flow,row),hooks[1],parameters=dict(parameters,lift_height=lift),
                         phase='carry',route=route,edges=edges,target=goal['target'])
        check=inspect(clone_robot(checker),flow.env,segments,item=item)
        rows.append(dict(row,id=row['id']+'|'+goal['id']+f'|{lift}|{route}',
                    goal=goal,lift=lift,transport_route=route,target=goal['target'],**check))
        if check['feasible']:
            return rows
    return rows


def prefix_search(flow, *, endpoints, parameters, hooks, edges, item):
    prefixes,candidates,skipped=[],[],0
    for option in options(flow):
        row=prepose(flow,option)
        goals=compatible(option,row,endpoints) if len(row['q1'])==6 else []
        if not goals:
            skipped+=1
            continue
        for route in ROUTES:
            if len(prefixes)>=MAX_PREFIX or len(candidates)>=MAX_CARRY:
                return prefixes,candidates,skipped,'search_budget_exhausted'
            segments=collect(proxy(flow,row),hooks[0],parameters=parameters,phase='prefix',route=route,edges=edges)
            checker=clone_robot(flow.robot)
            check=inspect(checker,flow.env,segments,item=item)
            current=dict(row,id=row['id']+'_'+route,approach_route=route,**check)
            prefixes.append(current)
            if len(prefixes)%16==0:
                print('path progress',len(prefixes),len(candidates),flush=True)
            if not check['feasible'] and check['phase']=='pregrasp':
                break
            if not check['feasible']:
                continue
            candidates.extend(transport(flow,current,checker,goals=goals,parameters=parameters,hooks=hooks,
                                        edges=edges,item=item,budget=MAX_CARRY-len(candidates)))
            if candidates and candidates[-1]['feasible']:
                return prefixes,candidates,skipped,'selected'
    return prefixes,candidates,skipped,'registered_candidates_exhausted'


def choose(flow, *, item, parameters, hooks, endpoints=None):
    before=state(flow.robot,flow.env)
    saved=context(flow,parameters)
    endpoints=endpoints if endpoints is not None else enumerate_goals(flow,item=item)
    print('endpoint passing',endpoints['passing'],flush=True)
    edges=corridor(flow.env,item['destination'])
    prefix,candidates,skipped,status=prefix_search(flow,endpoints=endpoints,parameters=parameters,
                                                hooks=hooks,edges=edges,item=item)
    unchanged(before,state(flow.robot,flow.env))
    return dict(context=saved,endpoints=endpoints,prefixes=prefix,candidates=candidates,status=status,
                selected=next((r for r in candidates if r['feasible']),None),skipped_prefixes=skipped,
                edges=[v.tolist() for v in edges],unchanged=True,
                limitations=['discrete_samples','open_gripper','rigid_held_object_translation','tracking_not_predicted'])
