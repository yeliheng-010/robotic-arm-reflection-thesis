"""无可行路径在动作记录器前退出；空轨迹不是遥测缺失失败。"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import route_runtime as runtime
from route_audit_v3 import validate_rejection
from test_runtime import ITEM, STATE, REPORT


class OrderingTests(unittest.TestCase):
    def test_rejection_never_calls_original_movement(self):
        flow = SimpleNamespace()
        with patch.object(runtime.grasp.GraspFlow, 'move_to_grasp_pose') as movement, \
             patch.object(runtime, 'choose', return_value=dict(selected=None, candidates=[])), \
             patch.object(runtime, 'abort', side_effect=RuntimeError('rejected')):
            with runtime.context(ITEM, STATE, {}, feedback=REPORT, excluded=set()), \
                 runtime.prepose.approach_context({}, ignore=('RedBlock','BlueBin')):
                with self.assertRaisesRegex(RuntimeError, 'rejected'):
                    runtime.grasp.GraspFlow.move_to_grasp_pose(flow)
            movement.assert_not_called()

    def test_empty_action_trace_with_raw_rejection(self):
        validate_rejection(dict(error={'evidence': {'route_planning_rejected': True}}),
                           dict(success=False), guard={'open_called': False}, rows=[])


if __name__ == '__main__':
    unittest.main()
