"""候选几何不变量及退化输入契约。"""
import unittest
import numpy as np
from grasp_process import generate_geometric_topdown_grasp as original
from geometry.candidates import generate


class CandidateTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.RandomState(17)
        self.points = rng.uniform([-.025, -.015, .79], [.025, .015, .81], (512, 3))

    def test_diverse_rotations(self):
        group = generate(self.points)
        self.assertEqual(6, len(group))
        rotations = group.rotation_matrices
        self.assertEqual(6, len(np.unique(rotations.round(8), axis=0)))
        for rotation in rotations:
            np.testing.assert_allclose(np.eye(3), rotation.T @ rotation, atol=1e-12)
            self.assertAlmostEqual(1., np.linalg.det(rotation))
            np.testing.assert_array_equal([0, 0, 1], rotation[:, 0])

    def test_preserves_original_and_input(self):
        before = self.points.copy()
        group = generate(self.points)
        np.testing.assert_array_equal(original(before).grasp_group_array[0], group.grasp_group_array[0])
        np.testing.assert_array_equal(before, self.points)
        self.assertTrue(np.all(group.scores[0] > group.scores[1:]))
        np.testing.assert_array_equal(group.grasp_group_array, generate(before).grasp_group_array)

    def test_width_and_center(self):
        group = generate(self.points)
        for grasp in group:
            self.assertLessEqual(grasp.width, .08)
            self.assertGreaterEqual(grasp.width, .02)
            np.testing.assert_array_equal(np.median(self.points, axis=0), grasp.translation)
        self.assertGreater(np.ptp(group.widths), .005)

    def test_rejects_nonfinite(self):
        self.points[0, 0] = np.nan
        with self.assertRaises(ValueError):
            generate(self.points)

    def test_rejects_degenerate(self):
        with self.assertRaises(ValueError):
            generate(np.tile([0, 0, .8], (64, 1)))

    def test_rejects_too_few_points(self):
        with self.assertRaises(ValueError):
            generate(self.points[:63])

    def test_capture_restored_on_exception(self):
        import grasp_process as grasp
        from geometry.runtime import capture_candidates
        original_inference = grasp.run_grasp_inference
        trace = {}
        with self.assertRaisesRegex(RuntimeError, 'test exception'):
            with capture_candidates('multi', trace):
                self.assertEqual(6, len(grasp.generate_geometric_topdown_grasp(self.points)))
                raise RuntimeError('test exception')
        self.assertIs(original_inference, grasp.run_grasp_inference)
        self.assertIs(original, grasp.generate_geometric_topdown_grasp)
        self.assertEqual(6, len(trace['generated']))


if __name__ == '__main__':
    unittest.main()

