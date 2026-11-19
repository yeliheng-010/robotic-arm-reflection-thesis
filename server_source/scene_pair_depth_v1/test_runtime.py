"""验证实际门禁适配，只修改被允许的单个观测像素。"""
import unittest
import numpy as np
from depth_runtime import validator
from reflection.monitors import validate_grounding
from reflection.errors import TaskAbort


class RuntimeTests(unittest.TestCase):
    def test_recovery_changes_only_missing_pixel(self):
        depth, roots = np.ones((9, 9)), np.ones((9, 9), dtype=int)
        depth[4, 4] = 0
        raw = depth.copy()
        events, arrays = [], {}
        value = validator(validate_grounding, events, arrays)([4, 4], depth, roots, 1)
        self.assertEqual((4, 4), value)
        self.assertEqual(1, np.count_nonzero(raw != depth))
        np.testing.assert_array_equal(raw, arrays['raw'])
        self.assertTrue(events[0]['accepted'])

    def test_wrong_target_remains_failure_without_mutation(self):
        depth, roots = np.ones((9, 9)), np.zeros((9, 9), dtype=int)
        depth[4, 4] = 0
        events, arrays = [], {}
        with self.assertRaises(TaskAbort):
            validator(validate_grounding, events, arrays)([4, 4], depth, roots, 1)
        self.assertEqual([], events)
        self.assertEqual(0, depth[4, 4])

    def test_valid_pixel_never_changes_sensor_or_creates_repair(self):
        depth, roots = np.full((9, 9), 1.003), np.ones((9, 9), dtype=int)
        events, arrays = [], {}
        validator(validate_grounding, events, arrays)([4, 4], depth, roots, 1)
        self.assertEqual([], events)
        self.assertEqual({}, arrays)
        self.assertTrue(np.all(depth == 1.003))
