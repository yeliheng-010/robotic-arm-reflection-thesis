import unittest
from unittest.mock import Mock,patch
from types import SimpleNamespace
import goal_runtime as runtime


class RuntimeTests(unittest.TestCase):
    def test_actual_target_reaches_flow_without_double_offset(self):
        selected=dict(target=[.9,.3,1.02],lift=.45)
        original=Mock(return_value='moved')
        result=runtime.placement(original,{'selected':selected})(None,(1,1,.74),z_offset=.12,lift_height=.35)
        self.assertEqual('moved',result)
        self.assertEqual((None,(.9,.3,1.02)),original.call_args.args)
        self.assertEqual(0.,original.call_args.kwargs['z_offset'])
        self.assertEqual(.45,original.call_args.kwargs['lift_height'])

    def test_inactive_leaves_all_hooks_unchanged(self):
        before=(runtime.prepose.select_prepose,runtime.grasp.move_to_point,runtime.grasp.GraspFlow.move_to_point)
        with runtime.context({'destination':'BlueBin'},{},{},previous_record={},previous_trace={}):
            self.assertEqual(before,(runtime.prepose.select_prepose,runtime.grasp.move_to_point,
                                     runtime.grasp.GraspFlow.move_to_point))

    def test_no_goal_aborts_before_movement(self):
        plan=dict(selected=None,status='search_budget_exhausted',endpoints={'passing':1})
        flow=SimpleNamespace(q1='untouched')
        with patch.object(runtime,'choose',return_value=plan),patch.object(runtime,'abort',side_effect=RuntimeError('abort')):
            with self.assertRaisesRegex(RuntimeError,'abort'):
                runtime.selector({}, {}, {}, hooks=())(flow,ignore=())
        self.assertEqual('untouched',flow.q1)


if __name__=='__main__':
    unittest.main()
