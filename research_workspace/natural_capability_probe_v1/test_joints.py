import unittest
import numpy as np
from rebuild_v3 import joints


class JointTests(unittest.TestCase):
    def test_unchanged_prepose_does_not_require_optional_q1(self):
        samples = np.linspace(np.zeros(6), np.ones(6), 51).tolist()
        bridge = dict(planners=[dict(executed=True, legs=[dict(samples=samples)],
                                    context=dict(robot_q=[0]*6))])
        q0, q1 = joints(bridge, dict(changed=False))
        np.testing.assert_array_equal([0]*6, q0)
        np.testing.assert_array_equal([1]*6, q1)

    def test_mismatching_recorded_q1_is_rejected(self):
        samples = np.linspace(np.zeros(6), np.ones(6), 51).tolist()
        bridge = dict(planners=[dict(executed=True, legs=[dict(samples=samples)],
                                    context=dict(robot_q=[0]*6))])
        with self.assertRaises(AssertionError):
            joints(bridge, dict(q1=[0]*6))


if __name__ == '__main__':
    unittest.main()
