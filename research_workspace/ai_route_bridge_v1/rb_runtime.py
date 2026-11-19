"""通用动作按显式参数启用，不接收或读取历史错误类别。"""
from contextlib import contextmanager
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
import stability.prepose as prepose
import goal_search
from goal_runtime import selector, placement
from waypoint_runtime import prefix_wrapper, carry_wrapper
from depth_runtime import context as depth_context
from nc_session import Session
from rb_common import save


@contextmanager
def route(item, state, trace):
    active = state['parameters']['replan']
    trace.update(active=active, activation='explicit_engineering_action', requested=state['parameters'])
    if not active:
        yield
        return
    assert state['profile'] == 'original'
    hooks = grasp.move_to_grasp_pose, grasp.move_to_point
    with patch.object(goal_search, 'LIFTS', (state['parameters']['lift_height'],)), \
         patch.object(prepose, 'select_prepose', selector(item, state['parameters'], trace, hooks=hooks)), \
         patch.object(grasp, 'move_to_grasp_pose', prefix_wrapper(hooks[0], trace)), \
         patch.object(grasp, 'move_to_point', carry_wrapper(hooks[1], trace)), \
         patch.object(grasp.GraspFlow, 'move_to_point', placement(grasp.GraspFlow.move_to_point, trace)):
        yield


class RouteSession(Session):
    def _engine(self):
        trace = {}
        try:
            with route(self.case['item'], self.state, trace):
                if self.state['parameters']['replan']:
                    with depth_context():
                        super()._engine()
                else:
                    super()._engine()
        finally:
            save(self.folder/'route.json', trace)
