import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import spatialmath as sm
import waypoint_runtime as runtime
from waypoint_paths import cartesian


class RuntimeTests(unittest.TestCase):
    def test_inactive_restores_all_hooks(self):
        before = runtime.prepose.select_prepose, runtime.grasp.move_to_grasp_pose, runtime.grasp.move_to_point
        with runtime.context(dict(destination='BlueBin'), {}, {}, previous_record={}, previous_trace={}):
            self.assertEqual(before, (runtime.prepose.select_prepose, runtime.grasp.move_to_grasp_pose,
                                      runtime.grasp.move_to_point))

    def test_carry_changes_only_transport_and_lift(self):
        trace = dict(selected=dict(lift=.45,transport_route='x_low'), edges=[[-1,-1],[1,1]])
        planners = [cartesian(sm.SE3(0,0,1),sm.SE3(.2,0,1),1.) for _ in range(3)]
        def original(*args, **kwargs):
            self.assertEqual(.45, kwargs['lift_height'])
            return runtime.grasp._run_planners(None,None,planners,[0.,1.,1.,1.],None)
        with patch.object(runtime.grasp,'_run_planners',return_value='done') as backend:
            self.assertEqual('done', runtime.carry_wrapper(original,trace)(None,None,lift_height=.35))
        values = backend.call_args.args
        self.assertEqual([0.,1.,2.,1.], values[3])
        self.assertIs(planners[0], values[2][0])
        self.assertIs(planners[2], values[2][2])

    def test_prefix_changes_only_approach(self):
        trace = dict(selected=dict(approach_route='y_high'), edges=[[-1,-1],[1,1]])
        planner = cartesian(sm.SE3(0,0,1),sm.SE3(.2,0,1),1.)
        def original(*args, **kwargs):
            for _ in range(3):
                runtime.grasp._run_planners(None,None,[planner],[0.,1.],None)
        with patch.object(runtime.grasp,'_run_planners') as backend:
            runtime.prefix_wrapper(original,trace)(None,None)
        self.assertEqual([[0.,1.],[0.,2.],[0.,1.]], [c.args[3] for c in backend.call_args_list])

    def test_no_route_aborts_before_mutating_flow(self):
        plan = dict(selected=None,prefixes=[],candidates=[])
        flow = SimpleNamespace(q1='untouched')
        with patch.object(runtime,'choose',return_value=plan), \
             patch.object(runtime,'abort',side_effect=RuntimeError('rejected')):
            with self.assertRaisesRegex(RuntimeError,'rejected'):
                runtime.selector({}, {}, {}, hooks=())(flow,ignore=())
        self.assertEqual('untouched',flow.q1)


if __name__ == '__main__':
    unittest.main()
