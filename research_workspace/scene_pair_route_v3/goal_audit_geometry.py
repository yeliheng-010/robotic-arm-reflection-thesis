"""重建选中端点和完整路径，不将静态通过等同于搬运成功。"""
from itertools import product
from unittest.mock import patch
import numpy as np
import spatialmath as sm
import grasp_process as grasp
from manipulator_grasp.arm.robot import UR5e
from stability.kinematics import set_robot_config
from route_audit_v3 import rebuild
from guard_scope import context as guard_context
from cm_pose import poses
from routecheck.clone import clone_robot
from route_geometry import inspect
from waypoint_search import proxy
from waypoint_paths import collect
from endpoint_geometry import measure
from goal_geometry import geometry,targets
from goal_policy import EDGE_MARGIN_M,MAX_PREFIX,MAX_CARRY


def endpoint_ledger(flow, trace):
    endpoint=trace['endpoints']
    assert endpoint['geometry']==geometry(flow,trace['item'])
    expected=[p['id']+'|'+','.join(map(str,c)) for p in poses(flow.T_wo) for c in product((1,-1),repeat=3)]
    assert [r['id'] for r in endpoint['grasps']]==expected
    goals=endpoint['goals']
    assert len(goals)==27*sum(r['ok'] for r in endpoint['grasps'])
    assert endpoint['passing']==sum(r['ok'] for r in goals)
    assert len(trace['prefixes'])<=MAX_PREFIX and len(trace['candidates'])<=MAX_CARRY
    selected=next((r for r in trace['candidates'] if r['feasible']),None)
    assert selected==trace['selected'] and trace['unchanged']


def selected_goal(flow, row, *, trace, item):
    dimensions=trace['endpoints']['geometry']
    pose=sm.SE3(np.array(row['pose']))
    goal=row['goal']
    candidates=list(targets(pose,dimensions))
    target=next(t for t in candidates if t['grid']==goal['grid'] and t['bottom_gap']==goal['bottom_gap'])
    np.testing.assert_allclose(target['target'],row['target'],atol=1e-12,rtol=0)
    np.testing.assert_allclose(target['object_center'],goal['object_center'],atol=1e-12,rtol=0)
    footprint=np.abs(np.array(goal['object_center'])[:2]-np.array(dimensions['bin_center'])[:2])
    footprint+=np.array(dimensions['source_half'])[:2]
    assert np.all(footprint<=np.array(dimensions['interior_half'])-EDGE_MARGIN_M+1e-12)
    release=sm.SE3.Rt(pose.R,row['target'])
    result=measure(flow,release,config=row['config'],item=item)
    assert result['ok']
    return result


def full_path(flow, row, *, trace, item):
    checker=clone_robot(flow.robot)
    parameters,edges=trace['context']['parameters'],np.array(trace['edges'])
    prefix=collect(proxy(flow,row),grasp.move_to_grasp_pose,parameters=parameters,
                   phase='prefix',route=row['approach_route'],edges=edges)
    assert inspect(checker,flow.env,prefix,item=item)['feasible']
    carry=collect(proxy(flow,row),grasp.move_to_point,parameters=dict(parameters,lift_height=row['lift']),
                  phase='carry',route=row['transport_route'],edges=edges,target=row['target'])
    assert inspect(checker,flow.env,carry,item=item)['feasible']
    return dict(prefix_legs=len(prefix),carry_legs=len(carry),passed=True)


def audit(case, trace):
    trace=dict(trace,item=case['item'])
    with patch.object(UR5e,'set_robot_config',set_robot_config),guard_context(case['item'],{}):
        flow=rebuild(case,trace)
        endpoint_ledger(flow,trace)
        row=trace['selected']
        if row is None:
            return dict(selected=False,status=trace['status'],full_search_repeated=False)
        endpoint=selected_goal(flow,row,trace=trace,item=case['item'])
        path=full_path(flow,row,trace=trace,item=case['item'])
    return dict(selected=True,endpoint=endpoint,path=path)
