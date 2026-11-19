import unittest
import numpy as np
import spatialmath as sm
from top_runtime import candidates, filter_context
from top_fit import estimate
from test_fit import fixture
import span_filter


class RuntimeTests(unittest.TestCase):
    def test_bounded_and_symmetric_candidates(self):
        fitted = estimate(fixture()[0])
        nominal = sm.SE3.Trans(*fitted['center'])
        rows = candidates(nominal, fitted)
        self.assertEqual(2, len(rows))
        np.testing.assert_allclose(rows[0]['pose'].R[:,1], -rows[1]['pose'].R[:,1])
        np.testing.assert_allclose([0,0,-1], rows[0]['pose'].R[:,0])
        self.assertEqual([], candidates(sm.SE3.Trans(3,3,3), fitted))
        self.assertEqual([], candidates(nominal, dict(available=False)))

    def test_context_restores_and_keeps_width_guard(self):
        points = fixture()[0]
        fitted, original = estimate(points), span_filter.original
        trace = {}
        with filter_context(points, trace):
            rows = span_filter.measured(sm.SE3.Trans(*fitted['center']), points)
            self.assertEqual(['observed_top_0','observed_top_180'], [r['id'] for r in rows])
            self.assertTrue(all(r['required_width_m'] >= r['observed_span_m'] for r in rows))
        self.assertIs(original, span_filter.original)
        self.assertEqual(fitted, trace['observed_top_estimate'])


if __name__ == '__main__':
    unittest.main()
