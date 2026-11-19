import unittest
from unittest.mock import patch
from types import SimpleNamespace
from self_geometry import forbidden, wrapper, context
import cm_geometry
import route_geometry
import goal_endpoints


class SelfTests(unittest.TestCase):
    def test_arm_and_gripper_penetration_rejected(self):
        self.assertTrue(forbidden(['ur5e_base', '2f85_base'], -.001))
        self.assertTrue(forbidden(['ur5e_base', 'ur5e_base'], -.001))

    def test_internal_gripper_and_external_delegated(self):
        self.assertFalse(forbidden(['2f85_base', '2f85_base'], -.01))
        self.assertFalse(forbidden(['ur5e_base', 'SortingTray'], -.01))
        self.assertFalse(forbidden(['ur5e_base', 'ur5e_base'], .001))

    def test_prior_failure_not_replaced(self):
        original = lambda *args, **kwargs: dict(ok=False, reason='ik_failure')
        self.assertEqual('ik_failure', wrapper(original)(None, None, None, value=None, ignore=())['reason'])

    def test_success_checked_and_scope_restored(self):
        original = cm_geometry.sample
        with context():
            self.assertIsNot(original, route_geometry.sample)
            self.assertIsNot(original, goal_endpoints.sample)
        self.assertIs(original, cm_geometry.sample)
        self.assertIs(original, goal_endpoints.sample)
        with patch('self_geometry.intersections', return_value=[dict(distance=-.01)]):
            check = wrapper(lambda *args, **kwargs: dict(ok=True))
            result = check(None, SimpleNamespace(mj_model=None), None, value=None, ignore=())
        self.assertEqual('robot_self_collision', result['reason'])


if __name__ == '__main__':
    unittest.main()
