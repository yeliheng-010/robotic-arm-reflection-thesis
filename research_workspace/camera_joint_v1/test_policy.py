import unittest
import math
from camera_joint_v1.policy import score, fovy_for_pixels


def row(index, pixels):
    return dict(index=index, framing=dict(passed=True),
        gate=dict(rejected=['Apple'], objects=dict(Apple=dict(visible_fraction=1., component_fraction=1.))),
        measurements=dict(Apple=dict(pixels=pixels, short_side=24, long_side=25)))


class PolicyTests(unittest.TestCase):
    def test_larger_visible_object_is_preferred(self):
        self.assertLess(score(row(1, 559)), score(row(0, 400)))

    def test_truth_does_not_influence_ranking(self):
        one = row(0, 559)
        self.assertEqual(score(one), score(dict(one, accurate=True, task_success=True)))

    def test_missing_object_measurement_is_ranked_as_bad(self):
        bad = row(0, 559)
        bad['gate']['objects']['Apple'] = dict(reasons=['invalid_measurement'])
        self.assertGreater(score(bad), score(row(1, 559)))

    def test_small_scene_tightens_to_original_lower_bound(self):
        self.assertEqual(48., fovy_for_pixels(dict(fovy=60.), [[220., 220.], [420., 420.]]))

    def test_scene_outside_upper_bound_is_rejected(self):
        self.assertIsNone(fovy_for_pixels(dict(fovy=60.), [[-200., -200.], [840., 840.]]))

    def test_snug_fovy_keeps_registered_margin(self):
        value = fovy_for_pixels(dict(fovy=60.), [[30., 30.], [610., 610.]])
        offset = 290 * math.tan(math.radians(30)) / math.tan(math.radians(value / 2))
        self.assertLessEqual(320 + offset, 614. + 1e-10)
        self.assertGreaterEqual(value, 48.)
        self.assertLess(value, 60.)

    def test_nonfinite_projection_is_rejected(self):
        self.assertIsNone(fovy_for_pixels(dict(fovy=60.), [[float('nan'), 0.]]))


if __name__ == '__main__':
    unittest.main()
