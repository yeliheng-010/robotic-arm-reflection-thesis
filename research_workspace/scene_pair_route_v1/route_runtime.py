"""仅目标箱碰撞反馈后的尝试使用重规划；退出后还原。"""
from contextlib import contextmanager
from unittest.mock import patch
import numpy as np
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
import stability.prepose as prepose
from reflection.monitors import abort, ErrorType
from route_policy import eligible
from route_search import choose


def selector(item, parameters, trace, *, excluded, hooks):
    def run(flow, *, ignore):
        plan = choose(flow, item=item, parameters=parameters, excluded=excluded, hooks=hooks)
        trace.update(plan)
        selected = plan['selected']
        if selected is None:
            abort(ErrorType.COLLISION, 'No certified route after destination collision',
                  route_planning_rejected=True, evaluated=len(plan['candidates']),
                  signal_source='simulation_geometry_route_search')
        flow.T_wo = sm.SE3(np.array(selected['pose']))
        flow.q1 = np.array(selected['q1'])
        return dict(changed=True, q1=selected['q1'], config=selected['config'],
                    route_id=selected['id'], validation='six_segment_static_with_destination_clearance')
    return run


@contextmanager
def context(item, state, trace, *, feedback, excluded):
    trace.update(active=eligible(feedback, item['destination']), feedback=feedback)
    if not trace['active']:
        yield
        return
    original = grasp.GraspFlow.move_to_point
    def carry(flow, *args, **kwargs):
        assert trace['selected'] is not None
        kwargs['lift_height'] = trace['selected']['lift']
        return original(flow, *args, **kwargs)
    hooks = (grasp.move_to_grasp_pose, grasp.move_to_point)
    with patch.object(prepose, 'select_prepose', selector(item, state['parameters'], trace, excluded=excluded, hooks=hooks)), \
         patch.object(grasp.GraspFlow, 'move_to_point', carry):
        yield
