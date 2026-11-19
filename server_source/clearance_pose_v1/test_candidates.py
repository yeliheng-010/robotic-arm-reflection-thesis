"""验证原候选保留和有限观测边界，禁止用无候选让断言空转。"""
import unittest
from copy import deepcopy
import numpy as np
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
from top_runtime import candidates as original
from cp_candidates import candidates


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.nominal = sm.SE3(1., .5, .8)
        self.fit = dict(available=True, center=[1., .5, .77], closing_axis=[1., 0., 0.],
                        top_z_m=.8, length_m=.1, width_m=.04)

    def test_original_two_are_preserved_first(self):
        rows = candidates(self.nominal, self.fit)
        self.assertGreaterEqual(len(rows), 2)
        for expected, actual in zip(original(self.nominal, self.fit), rows):
            self.assertEqual(expected['id'], actual['id'])
            np.testing.assert_array_equal(expected['pose'].A, actual['pose'].A)

    def test_expansion_is_unique_bounded_and_internal(self):
        rows = candidates(self.nominal, self.fit)
        self.assertGreater(len(rows), 2)
        self.assertLessEqual(len(rows), 30)
        matrices = {tuple(np.round(row['pose'].A.flatten(), 12)) for row in rows}
        self.assertEqual(len(rows), len(matrices))
        for row in rows:
            center = row['pose'].t
            self.assertLessEqual(np.linalg.norm(center-self.nominal.t), .050+1e-12)
            self.assertAlmostEqual(1., center[0])
            self.assertLessEqual(abs(center[1]-.5), min(.020, .2*self.fit['length_m'])+1e-12)
            self.assertTrue(any(abs((.8-center[2])-depth)<1e-12 for depth in (.030,.020,.015)))
            self.assertAlmostEqual(1., abs(row['pose'].R[:,1] @ [1.,0.,0.]))

    def test_distant_or_unavailable_observation_cannot_create_candidate(self):
        self.assertEqual([], candidates(sm.SE3(10.,10.,10.), self.fit))
        self.assertEqual([], candidates(self.nominal, dict(available=False)))

    def test_invalid_fit_is_rejected(self):
        for field, value in (('center', [np.nan,0.,0.]), ('length_m', 0.),
                             ('width_m', -.1), ('closing_axis', [0.,0.,0.])):
            fitted = deepcopy(self.fit)
            fitted[field] = value
            self.assertEqual([], candidates(self.nominal, fitted))


if __name__ == '__main__':
    unittest.main()
