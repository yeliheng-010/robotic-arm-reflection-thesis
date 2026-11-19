import unittest
import numpy as np
import spatialmath as sm
from rebuild_v2 import nominal_pose


class PoseTests(unittest.TestCase):
    def fixture(self):
        nominal = sm.SE3.Rt(sm.SO3.RPY([.2, .3, .4]).R, [1.4, .4, .8])
        approach = nominal * sm.SE3(-.1, 0, 0)
        bridge = dict(grasp=dict(actual_target=nominal.t.tolist()), planners=[{},
            dict(executed=False, legs=[dict(samples=[approach.A.tolist()])])])
        return nominal, bridge

    def test_recovers_nominal_from_local_approach_offset(self):
        expected, bridge = self.fixture()
        np.testing.assert_allclose(expected.A, nominal_pose(bridge).A, atol=1e-9, rtol=0)

    def test_wrong_target_is_rejected(self):
        _, bridge = self.fixture()
        bridge['grasp']['actual_target'][0] += .001
        with self.assertRaises(AssertionError):
            nominal_pose(bridge)

    def test_unregistered_phase_is_rejected(self):
        _, bridge = self.fixture()
        bridge['planners'][-1]['executed'] = True
        with self.assertRaises(AssertionError):
            nominal_pose(bridge)


if __name__ == '__main__':
    unittest.main()
