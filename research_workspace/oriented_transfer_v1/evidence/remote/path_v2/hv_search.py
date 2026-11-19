"""分解前缀检查与搜索控制；沿用已登记的有预算路线。"""
import grasp_process as grasp
import waypoint_search
from waypoint_paths import collect,corridor
from waypoint_policy import ROUTES
from route_geometry import inspect
from routecheck.clone import clone_robot
from jg_geometry import Advisor
from hp_carry import carry
from hp_search import MAX_PREFIX,MAX_CARRY,eligible


def row_goals(flow, option, goals):
    row=waypoint_search.prepose(flow,option)
    name=option['id'].rsplit('_safe',1)[0] if option['rise'] is None else option['id'].rsplit('_',2)[0]
    row['pose_name']=name
    return row,eligible(row,goals) if len(row['q1'])==6 else []


def attempt(flow, row, route, *, item, parameters, goals, edges, rows, record):
    proxy=waypoint_search.proxy(flow,row)
    proxy.joint_option=row.get('joint_option')
    segments=collect(proxy,grasp.move_to_grasp_pose,parameters=parameters,phase='prefix',route=route,edges=edges)
    checker=clone_robot(flow.robot)
    check=inspect(checker,flow.env,segments,item=item)
    current=dict(row,id=row['id']+'_'+route,approach_route=route,**check)
    rows['prefixes'].append(current)
    record('prefix',current)
    selected=None
    if check['feasible']:
        selected=carry(flow,current,checker,goals=goals,parameters=parameters,item=item,
            ledger=rows['carry'],maximum=MAX_CARRY,record=record)
    return current,selected


def done(selected, status, rows):
    return dict(rows,selected=selected,status=status)


def explore(flow, *, item, parameters, goals, record):
    rows=dict(prefixes=[],carry=[],events=[])
    advisor=Advisor(flow,item=item,parameters=parameters,record=rows['events'].append)
    edges=corridor(flow.env,item['destination'])
    for option in waypoint_search.options(flow):
        row,targets=row_goals(flow,option,goals)
        if not targets:
            continue
        row=advisor.choose(row)
        if row is None:
            continue
        for route in ROUTES:
            if len(rows['prefixes'])>=MAX_PREFIX or len(rows['carry'])>=MAX_CARRY:
                return done(None,'path_budget_exhausted',rows)
            current,selected=attempt(flow,row,route,item=item,parameters=parameters,goals=targets,
                edges=edges,rows=rows,record=record)
            if selected:
                return done(selected,'selected',rows)
            if not current['feasible'] and current['phase']=='pregrasp':
                break
    return done(None,'registered_paths_exhausted',rows)
