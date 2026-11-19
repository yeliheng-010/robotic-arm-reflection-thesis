import importlib.util
import unittest


class VisibilityPolicyTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('cv_policy'), '缺少全部物体轻遮挡门槛')
        self.policy = __import__('cv_policy')

    def row(self, **changes):
        row = dict(pixels=850, isolated_pixels=1000, short_side=20,
                   largest_component=800, framed=True)
        row.update(changes)
        return row

    def test_boundary_visible_object_passes(self):
        self.assertTrue(self.policy.object_gate(self.row())['passed'])

    def test_occluded_non_target_rejects_whole_frame(self):
        rows = {name: self.row() for name in self.policy.REQUIRED}
        rows['GreenCylinder'] = self.row(pixels=8, isolated_pixels=1406)
        report = self.policy.frame_gate(rows)
        self.assertFalse(report['passed'])
        self.assertIn('GreenCylinder', report['rejected'])

    def test_background_object_is_required(self):
        rows = {name: self.row() for name in self.policy.REQUIRED}
        del rows['Knife']
        self.assertFalse(self.policy.frame_gate(rows)['passed'])

    def test_tiny_or_fragmented_or_clipped_objects_reject(self):
        for changes in [dict(pixels=575, isolated_pixels=575), dict(short_side=15),
                        dict(largest_component=679), dict(framed=False),
                        dict(pixels=849)]:
            with self.subTest(changes=changes):
                self.assertFalse(self.policy.object_gate(self.row(**changes))['passed'])

    def test_invalid_measurements_fail_closed(self):
        for changes in [dict(pixels=float('nan')), dict(isolated_pixels=0),
                        dict(short_side=-1), dict(largest_component=851),
                        dict(pixels=True)]:
            with self.subTest(changes=changes):
                self.assertFalse(self.policy.object_gate(self.row(**changes))['passed'])

    def test_small_rasterization_difference_does_not_break_visibility(self):
        self.assertTrue(self.policy.object_gate(self.row(pixels=1001, largest_component=1001))['passed'])

    def test_downstream_cannot_use_rejected_frame(self):
        with self.assertRaises(ValueError):
            self.policy.require_frame(dict(passed=False, rejected=['Knife']))

    def test_mask_metrics_distinguish_fragmented_objects(self):
        import numpy as np
        from cv_metrics import mask_metrics
        mask = np.zeros((80, 80), dtype=bool)
        mask[2:22, 2:22] = True
        mask[42:62, 42:62] = True
        row = mask_metrics(mask)
        self.assertEqual(800, row['pixels'])
        self.assertEqual(400, row['largest_component'])
        row.update(isolated_pixels=800, framed=True)
        self.assertFalse(self.policy.object_gate(row)['passed'])

    def test_empty_mask_is_rejected(self):
        import numpy as np
        from cv_metrics import mask_metrics
        row = mask_metrics(np.zeros((40, 40), dtype=bool))
        row.update(isolated_pixels=1000, framed=True)
        self.assertEqual(0, row['pixels'])
        self.assertFalse(self.policy.object_gate(row)['passed'])

    def test_spurious_pixels_outside_isolated_outline_do_not_count(self):
        import numpy as np
        import cv_metrics
        self.assertTrue(hasattr(cv_metrics, 'object_metrics'), '应按隔离轮廓限制可见像素')
        isolated = np.zeros((80, 80), dtype=bool)
        isolated[10:40, 10:40] = True
        full = isolated.copy()
        full[70, 70] = True
        row = cv_metrics.object_metrics(full, isolated)
        self.assertEqual(900, row['pixels'])
        self.assertEqual(900, row['isolated_pixels'])
        self.assertEqual(30, row['short_side'])


if __name__ == '__main__':
    unittest.main()
