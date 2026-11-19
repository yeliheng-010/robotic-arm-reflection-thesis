"""先在Flow层传递最终目标，再使用原执行记录器和释放保护。"""
from contextlib import contextmanager
from unittest.mock import patch
import numpy as np
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
import stability.prepose as prepose
from reflection.monitors import abort,ErrorType
from waypoint_policy import allowed
from waypoint_runtime import prefix_wrapper,carry_wrapper
from goal_search import choose


def selector(item, parameters, trace, *, hooks):
    def run(flow, *, ignore):
        plan=choose(flow,item=item,parameters=parameters,hooks=hooks)
        trace.update(plan)
        selected=plan['selected']
        if selected is None:
            abort(ErrorType.COLLISION,'No certified legal-placement route',route_planning_rejected=True,
                  planning_status=plan['status'],endpoint_passing=plan['endpoints']['passing'])
        flow.T_wo,flow.q1=sm.SE3(np.array(selected['pose'])),np.array(selected['q1'])
        return dict(changed=True,q1=selected['q1'],config=selected['config'],route_id=selected['id'])
    return run


def placement(original, trace):
    def move(flow, target_place, **kwargs):
        selected=trace['selected']
        kwargs.update(z_offset=0.,lift_height=selected['lift'])
        return original(flow,tuple(selected['target']),**kwargs)
    return move


@contextmanager
def context(item, state, trace, *, previous_record, previous_trace):
    active=allowed(previous_record,previous_trace,item['destination'])
    trace.update(active=active,collision_feedback=previous_trace.get('feedback'))
    if not active:
        yield
        return
    assert state['profile']=='original'
    hooks=grasp.move_to_grasp_pose,grasp.move_to_point
    with patch.object(prepose,'select_prepose',selector(item,state['parameters'],trace,hooks=hooks)), \
         patch.object(grasp,'move_to_grasp_pose',prefix_wrapper(hooks[0],trace)), \
         patch.object(grasp,'move_to_point',carry_wrapper(hooks[1],trace)), \
         patch.object(grasp.GraspFlow,'move_to_point',placement(grasp.GraspFlow.move_to_point,trace)):
        yield
