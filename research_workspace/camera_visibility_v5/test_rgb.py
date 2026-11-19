import importlib.util
import unittest
import numpy as np


class RgbConsistencyTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('cv_rgb'), '缺少渲染量化差异判定')
        return __import__('cv_rgb')

    def test_only_sparse_two_level_rgb_noise_is_allowed(self):
        module = self.module()
        old = np.zeros((100, 100, 3), dtype=np.uint8)
        new = old.copy()
        new[0, 0, 0] = 2
        self.assertTrue(module.compare(old, new)['passed'])
        new[0, 0, 0] = 3
        self.assertFalse(module.compare(old, new)['passed'])

    def test_large_changed_area_or_size_change_is_rejected(self):
        module = self.module()
        old = np.zeros((100, 100, 3), dtype=np.uint8)
        new = old.copy()
        new[0, :, 0] = 1
        self.assertFalse(module.compare(old, new)['passed'])
        self.assertFalse(module.compare(old, new[:50])['passed'])
