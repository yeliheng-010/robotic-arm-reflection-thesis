import unittest
import numpy as np
from sensor_independent_v2.rgb_policy import assess, qualify


class RgbTests(unittest.TestCase):
    def setUp(self):
        self.before = np.zeros((100, 100, 3), dtype=np.uint8)

    def test_sparse_quantization_is_not_bitwise_identity(self):
        after = self.before.copy()
        after[0, 0, 0] = 2
        result = assess(self.before, after)
        self.assertTrue(result['passed'])
        self.assertFalse(result['bitwise_equal'])
        self.assertNotEqual(result['before_sha256'], result['after_sha256'])

    def test_large_amplitude_is_rejected(self):
        after = self.before.copy()
        after[0, 0, 0] = 3
        self.assertFalse(assess(self.before, after)['passed'])

    def test_large_area_is_rejected(self):
        after = self.before.copy()
        after[0, :11, 0] = 1
        self.assertFalse(assess(self.before, after)['passed'])

    def test_rgb_failure_cannot_produce_usable_geometry(self):
        report = dict(gate=dict(passed=True), calibration=dict(passed=True))
        result = qualify(report, dict(passed=False))
        self.assertTrue(result['geometry_accepted'])
        self.assertFalse(result['accepted'])
        self.assertNotIn('geometry_accepted', report)

    def test_rgb_pass_cannot_override_calibration_failure(self):
        report = dict(gate=dict(passed=True), calibration=dict(passed=False))
        self.assertFalse(qualify(report, dict(passed=True))['accepted'])
