import unittest
import spatialmath as sm
from loopstudy.actions import initial
from cm_pose import poses
from rv_common import change
from rv_runtime import ordered, mode, goal_endpoints, waypoint_search, goal_audit_geometry


class VerticalTests(unittest.TestCase):
    def test_sort_preserves_all_poses_and_prioritizes_world_down(self):
        nominal = sm.SE3(.2, .3, .8)
        before, after = poses(nominal), ordered(nominal)
        self.assertEqual(sorted(r['id'] for r in before), sorted(r['id'] for r in after))
        self.assertEqual('original', after[-1]['id'])
        for row in before:
            self.assertTrue((row['pose'].A == next(r['pose'].A for r in after if r['id']==row['id'])).all())

    def test_control_does_not_silently_change_engine_parameters(self):
        state, control = change(initial(), dict(grasp_mode='original'), action='SAFE_ROUTE')
        updated, selected = change(state, control, action='WORLD_DOWN_ROUTE')
        self.assertEqual(state, updated)
        self.assertEqual(dict(grasp_mode='original'), control)
        self.assertEqual(dict(grasp_mode='world_down'), selected)

    def test_runtime_and_audit_order_share_scope_and_restore(self):
        modules = (goal_endpoints, waypoint_search, goal_audit_geometry)
        before = [m.poses for m in modules]
        with mode(dict(grasp_mode='world_down')):
            self.assertEqual([ordered]*3, [m.poses for m in modules])
        self.assertEqual(before, [m.poses for m in modules])

    def test_unknown_control_rejected(self):
        with self.assertRaises(AssertionError):
            with mode(dict(grasp_mode='hidden_fix')):
                pass


if __name__ == '__main__':
    unittest.main()
