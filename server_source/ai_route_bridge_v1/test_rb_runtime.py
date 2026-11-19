from copy import deepcopy
import unittest
from unittest.mock import patch
from loopstudy.actions import initial
from rb_common import change
import rb_runtime


class RuntimeTests(unittest.TestCase):
    def test_route_action_preserves_unrelated_parameters(self):
        before = initial()
        expected = deepcopy(before)
        expected['parameters'].update(replan=True, lift_height=.15)
        self.assertEqual(expected, change(before, 'SAFE_ROUTE'))
        self.assertEqual(initial(), before)

    def test_slow_requires_route_and_changes_only_time(self):
        with self.assertRaises(AssertionError):
            change(initial(), 'SLOW_ROUTE')
        before = change(initial(), 'SAFE_ROUTE')
        expected = deepcopy(before)
        expected['parameters']['time_scale'] = 1.5
        self.assertEqual(expected, change(before, 'SLOW_ROUTE'))

    def test_inactive_does_not_change_grasp_or_placement(self):
        hooks = rb_runtime.grasp.move_to_grasp_pose, rb_runtime.grasp.GraspFlow.move_to_point
        trace = {}
        with rb_runtime.route({}, initial(), trace):
            self.assertEqual(hooks, (rb_runtime.grasp.move_to_grasp_pose, rb_runtime.grasp.GraspFlow.move_to_point))
        self.assertFalse(trace['active'])

    def test_active_uses_explicit_height_without_hidden_feedback(self):
        state, trace = change(initial(), 'SAFE_ROUTE'), {}
        before = rb_runtime.goal_search.LIFTS
        with rb_runtime.route(dict(source='Block', destination='Bin'), state, trace):
            self.assertEqual((.15,), rb_runtime.goal_search.LIFTS)
            self.assertTrue(trace['active'])
        self.assertEqual(before, rb_runtime.goal_search.LIFTS)

    def test_unknown_action_rejected(self):
        with self.assertRaises(ValueError):
            change(initial(), 'SECRET_FIX')


if __name__ == '__main__':
    unittest.main()
