import unittest
from sensor_independent_v1.assessment import transitions, ray_metrics, ray_nonregression


class AssessmentTests(unittest.TestCase):
    def test_regressions_not_hidden_by_net_gain(self):
        self.assertEqual(dict(total=4, original_pass=2, no_msaa_pass=3, gained=2, lost=1),
                         transitions([(False, True), (False, True), (True, False), (True, True)]))

    def test_missing_ray_is_retained_and_never_counts_as_accuracy(self):
        result = ray_metrics([dict(ray_depth_m=None)])
        self.assertEqual(1, result['missing'])
        self.assertEqual(0, result['valid'])
        self.assertFalse(ray_nonregression(result))

    def test_root_mismatch_blocks_even_if_depth_improves(self):
        row = dict(ray_depth_m=1., ray_root=1, original=dict(depth_m=1.02, root=1),
                   no_msaa=dict(depth_m=1.0001, root=2))
        self.assertFalse(ray_nonregression(ray_metrics([row])))


if __name__ == '__main__':
    unittest.main()
