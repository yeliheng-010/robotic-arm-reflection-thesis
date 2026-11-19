from pathlib import Path
from unittest.mock import patch
import grasp_process as grasp
import goal_search
from qualify import reference
from audit_motion_live import UR5e, set_robot_config, guard_context
from rv_runtime import mode
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from span_filter import context as span_context
from sr_common import change
from f_common import save, sha

ROOT = Path(__file__).resolve().parent
LIFT_M = .20


def qualify(case, template, points):
    name = case['item']['id']
    if not case['config']['geometry_accepted'] or not case['config']['compiled_check']['passed']:
        return dict(id=name, passed=False, status='layout_geometry_rejected')
    trace = {}
    with patch.object(UR5e, 'set_robot_config', set_robot_config), guard_context(case['item'], {}), \
         self_context(), joint_context(case['config']), span_context(points, trace), \
         mode(dict(grasp_mode='world_down')), patch.object(goal_search, 'LIFTS', (LIFT_M,)):
        flow = reference(case, template)
        state, _ = change(case['state'], dict(grasp_mode='original'), action='SELF_SAFE_ROUTE')
        state['parameters']['lift_height'] = LIFT_M
        plan = goal_search.choose(flow, item=case['item'], parameters=state['parameters'],
            hooks=(grasp.move_to_grasp_pose, grasp.move_to_point))
    path = ROOT/'plans'/(name+'.json')
    save(path, plan)
    return dict(id=name, passed=plan['selected'] is not None, status=plan['status'],
        passing_endpoints=plan['endpoints']['passing'], selected=(plan['selected'] or {}).get('id'),
        path=str(path), sha256=sha(path), span_filter=trace, lift_height=LIFT_M)
