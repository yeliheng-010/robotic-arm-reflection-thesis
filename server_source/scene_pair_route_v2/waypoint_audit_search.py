"""核对固定枚举和剪枝完整性；成功候选重新逐腿计算。"""
from unittest.mock import patch
import numpy as np
import grasp_process as grasp
from manipulator_grasp.arm.robot import UR5e
from stability.kinematics import set_robot_config
from guard_scope import context as guard_context
from route_audit_v3 import rebuild
from routecheck.clone import clone_robot
from route_geometry import inspect
from waypoint_search import options, proxy
from waypoint_paths import collect
from waypoint_policy import ROUTES, LIFTS


def base_id(row, known):
    if row['id'] in known:
        return row['id']
    for route in ROUTES:
        suffix = '_'+route
        if row['id'].endswith(suffix) and row['id'][:-len(suffix)] in known:
            return row['id'][:-len(suffix)]
    raise AssertionError('Unknown prefix '+row['id'])


def ledger(flow, trace):
    expected = [r['id'] for r in options(flow)]
    groups = {}
    for row in trace['prefixes']:
        key = base_id(row, set(expected))
        groups.setdefault(key, []).append(row)
    assert list(groups) == expected[:len(groups)]
    if trace['selected'] is None:
        assert len(groups) == len(expected)
    for index, rows in enumerate(groups.values()):
        prefix_group(rows, final_selected=trace['selected'] is not None and index == len(groups)-1)
    ids = [r['id']+'_'+str(lift)+'_'+route for r in trace['prefixes'] if r['feasible']
           for lift in LIFTS for route in ROUTES]
    assert [r['id'] for r in trace['candidates']] == ids[:len(trace['candidates'])]
    selected = next((r for r in trace['candidates'] if r['feasible']), None)
    assert selected == trace['selected']
    if selected is None:
        assert len(trace['candidates']) == len(ids)
    else:
        assert trace['candidates'][-1] == selected
    assert trace['unchanged']


def prefix_group(rows, *, final_selected):
    if (rows[0].get('failure') or {}).get('reason') == 'prepose_ik':
        assert len(rows) == 1 and not rows[0]['q1']
        return
    assert [r['approach_route'] for r in rows] == list(ROUTES[:len(rows)])
    early = rows[0].get('phase') == 'pregrasp' and not rows[0]['feasible']
    if early:
        assert len(rows) == 1
    elif not final_selected:
        assert len(rows) == len(ROUTES)


def selected_geometry(flow, row, *, trace, item):
    checker = clone_robot(flow.robot)
    edges, parameters = np.array(trace['edges']), trace['context']['parameters']
    prefix = collect(proxy(flow,row), grasp.move_to_grasp_pose, parameters=parameters,
                     phase='prefix', route=row['approach_route'], edges=edges)
    assert inspect(checker, flow.env, prefix, item=item)['feasible']
    carry = collect(proxy(flow,row), grasp.move_to_point,
                    parameters=dict(parameters,lift_height=row['lift']), phase='carry',
                    route=row['transport_route'], edges=edges, target=row['target'])
    assert inspect(checker, flow.env, carry, item=item)['feasible']


def audit(case, trace):
    with patch.object(UR5e,'set_robot_config',set_robot_config), guard_context(case['item'],{}):
        flow = rebuild(case,trace)
        ledger(flow,trace)
        if trace['selected']:
            selected_geometry(flow,trace['selected'],trace=trace,item=case['item'])
    return dict(enumeration_checked=True, selected_recomputed=trace['selected'] is not None,
                full_negative_search_repeated=False)
