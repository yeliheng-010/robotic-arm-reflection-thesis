import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock
import numpy as np
import route_runtime as runtime

ITEM = dict(source='RedBlock', destination='BlueBin')
STATE = dict(parameters={'lift_height': .35})
REPORT = dict(error_type='collision', evidence={'contacts': [['ur5e_base', 'BlueBin']]})


class RuntimeTests(unittest.TestCase):
    def test_inactive_changes_no_hooks(self):
        before = runtime.prepose.select_prepose, runtime.grasp.GraspFlow.move_to_point
        with patch.object(runtime, 'choose') as search:
            with runtime.context(ITEM, STATE, {}, feedback=None, excluded=set()):
                self.assertEqual(before, (runtime.prepose.select_prepose, runtime.grasp.GraspFlow.move_to_point))
            search.assert_not_called()

    def test_selected_pose_joints_and_lift_reach_execution(self):
        selected = dict(id='probe', pose=np.eye(4).tolist(), q1=[1.]*6, config=[1,1,1], lift=.55)
        flow, trace = SimpleNamespace(), {}
        plan = dict(selected=selected, candidates=[selected])
        with patch.object(runtime, 'choose', return_value=plan), \
             patch.object(runtime.grasp.GraspFlow, 'move_to_point', return_value='executed') as carry:
            with runtime.context(ITEM, STATE, trace, feedback=REPORT, excluded=set()):
                runtime.prepose.select_prepose(flow, ignore=('RedBlock','BlueBin'))
                self.assertEqual('executed', runtime.grasp.GraspFlow.move_to_point(flow, (0,0,0), lift_height=.35))
        np.testing.assert_array_equal(selected['pose'], flow.T_wo.A)
        np.testing.assert_array_equal(selected['q1'], flow.q1)
        self.assertEqual(.55, carry.call_args.kwargs['lift_height'])

    def test_no_route_aborts_before_physical_motion(self):
        plan = dict(selected=None, candidates=[])
        flow = SimpleNamespace(q1='untouched', T_wo='untouched')
        with patch.object(runtime, 'choose', return_value=plan), \
             patch.object(runtime, 'abort', side_effect=RuntimeError('rejected')) as abort:
            with runtime.context(ITEM, STATE, {}, feedback=REPORT, excluded=set()):
                with self.assertRaisesRegex(RuntimeError, 'rejected'):
                    runtime.prepose.select_prepose(flow, ignore=('RedBlock','BlueBin'))
        self.assertTrue(abort.call_args.kwargs['route_planning_rejected'])
        self.assertEqual('untouched', flow.q1)


if __name__ == '__main__':
    unittest.main()
