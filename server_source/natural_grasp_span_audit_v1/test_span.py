import unittest
import numpy as np
from span import span


class SpanTests(unittest.TestCase):
    def test_long_and_short_axes_remain_distinct_under_translation(self):
        x, y = np.meshgrid(np.linspace(-.08, .08, 30), np.linspace(-.02, .02, 30))
        points = np.column_stack((x.ravel(), y.ravel(), np.zeros(x.size)))
        self.assertGreater(span(points, [1,0,0]), .08)
        self.assertLess(span(points, [0,1,0]), .08)
        self.assertAlmostEqual(span(points, [1,0,0]), span(points+[4,2,1], [-1,0,0]))

    def test_invalid_axis_and_nonfinite_input_rejected(self):
        points = np.zeros((64,3))
        with self.assertRaises(AssertionError):
            span(points, [0,0,0])
        points[0,0] = np.nan
        with self.assertRaises(AssertionError):
            span(points, [1,0,0])
