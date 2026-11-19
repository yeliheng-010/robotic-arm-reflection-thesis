import unittest
import numpy as np
import spatialmath as sm
from span_filter import measured


class SpanFilterTests(unittest.TestCase):
    def test_pose_rotation_rechecks_opening_requirement(self):
        x, y = np.meshgrid(np.linspace(-.08, .08, 30), np.linspace(-.02, .02, 30))
        points = np.column_stack((x.ravel(), y.ravel(), np.zeros(x.size)))
        nominal = sm.SE3.Rt(sm.SO3.TwoVectors(x=[0.,0.,-1.], y=[0.,1.,0.]), [.5,.6,.8])
        rows = {r['id']:r for r in measured(nominal, points)}
        self.assertTrue(rows['world_down_0']['passed'])
        self.assertFalse(rows['world_down_90']['passed'])
        self.assertFalse(rows['world_down_-90']['passed'])

    def test_margin_is_retained_not_widened(self):
        x, y = np.meshgrid(np.linspace(-.04, .04, 30), np.linspace(-.04, .04, 30))
        points = np.column_stack((x.ravel(), y.ravel(), np.zeros(x.size)))
        nominal = sm.SE3()
        rows = measured(nominal, points)
        for row in rows:
            self.assertAlmostEqual(.012, row['required_width_m']-row['observed_span_m'])
            self.assertEqual(row['required_width_m'] <= .08, row['passed'])
