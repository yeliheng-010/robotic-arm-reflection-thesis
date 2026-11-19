"""随机化必须可复现、受限且不污染输入或封存任务组合。"""
import unittest
import numpy as np
from diversity.config import scenario, task_matrix, PROFILES
from diversity.noise import corrupt_depth


class RandomizationTests(unittest.TestCase):
    def test_determinism_and_severity_independent_fault(self):
        first = scenario(61001, 'medium')
        self.assertEqual(first, scenario(61001, 'medium'))
        self.assertNotEqual(first, scenario(61002, 'medium'))
        self.assertEqual(first['faults'], scenario(61001, 'clean')['faults'])

    def test_clean_depth_exact_and_input_preserved(self):
        depth = np.array([[1., 0., np.nan], [2., 3., 4.]], dtype=np.float32)
        original = depth.copy()
        noisy, stats = corrupt_depth(depth, PROFILES['clean'], seed=2)
        np.testing.assert_equal(depth, noisy)
        np.testing.assert_equal(original, depth)
        self.assertEqual(0, stats['dropped_pixels'])

    def test_noise_is_reproducible_and_measurable(self):
        depth = np.ones((300, 300), dtype=np.float32)
        first, stats = corrupt_depth(depth, PROFILES['medium'], seed=8)
        second, _ = corrupt_depth(depth, PROFILES['medium'], seed=8)
        third, _ = corrupt_depth(depth, PROFILES['medium'], seed=9)
        np.testing.assert_array_equal(first, second)
        self.assertFalse(np.array_equal(first, third))
        self.assertTrue(np.all(depth == 1))
        self.assertTrue(0.015 < stats['dropout_fraction'] < 0.025)
        self.assertTrue(0.0028 < stats['noise_rmse_m'] < 0.0032)
        self.assertTrue(np.all(np.isfinite(first)) and np.all(first >= 0))

    def test_task_matrix_preserves_group_split(self):
        tasks = task_matrix(seeds_per_group=2)
        self.assertEqual(320, len(tasks))
        forbidden = {('PurpleCapsule', 'SortingTray'), ('OrangeSphere', 'RedBin')}
        groups = {}
        for task in tasks:
            pair = task['source'], task['destination']
            self.assertNotIn(pair, forbidden)
            groups.setdefault(pair, set()).add(task['split'])
        self.assertTrue(all(len(splits) == 1 for splits in groups.values()))

    def test_invalid_profiles_and_seeds_fail(self):
        for seed, profile in [(-1, 'light'), (1, 'unknown')]:
            with self.assertRaises(ValueError):
                scenario(seed, profile)


if __name__ == '__main__':
    unittest.main()
