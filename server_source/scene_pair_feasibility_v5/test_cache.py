"""旧版本拒绝行未记录深度字段，复用时必须视作尚未检查。"""
import unittest
from sf_cache import normalized


class CacheTests(unittest.TestCase):
    def test_missing_depth_is_unchecked_not_accepted(self):
        old = dict(index=2, accepted=True, camera={}, framing=dict(passed=True), visibility={})
        current = normalized(old)
        self.assertIsNone(current['calibration'])
        self.assertFalse(current['accepted'])
        self.assertNotIn('calibration', old)
        self.assertTrue(old['accepted'])

    def test_recorded_failed_depth_is_preserved(self):
        old = dict(calibration=dict(passed=False, max_outside_bounds_m=.013))
        self.assertEqual(old['calibration'], normalized(old)['calibration'])
