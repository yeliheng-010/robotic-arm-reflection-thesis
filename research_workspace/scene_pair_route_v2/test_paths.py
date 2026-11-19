import unittest
import numpy as np
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
from waypoint_paths import cartesian, detour, expand, waypoint
from waypoint_policy import ROUTES


class PathTests(unittest.TestCase):
    def test_direct_preserves_planner_and_time(self):
        planner = cartesian(sm.SE3(0,0,1), sm.SE3(1,1,1), 1.)
        actual, duration = detour(planner, 1., route='direct', edges=None)
        self.assertIs(planner, actual)
        self.assertEqual(1., duration)

    def test_detours_keep_endpoints_and_sample_each_leg(self):
        start, end = sm.SE3(0,0,1), sm.SE3(1,1,.9)
        edges = np.array([-.2,-.3]), np.array([1.2,1.3])
        for route in ROUTES[1:]:
            planner, duration = detour(cartesian(start,end,1.), 1., route=route, edges=edges)
            self.assertEqual(2., duration)
            np.testing.assert_allclose(start.A, planner.interpolate(0).A, atol=1e-12)
            np.testing.assert_allclose(end.A, planner.interpolate(2).A, atol=1e-12)
            np.testing.assert_allclose(waypoint(start,end,route,edges=edges).A,
                                       planner.interpolate(1).A, atol=1e-12)
            self.assertEqual(2, len(expand('transport',planner,duration)))


if __name__ == '__main__':
    unittest.main()
