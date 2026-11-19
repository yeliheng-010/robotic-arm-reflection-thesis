"""固定失败点云为开发回归，真值只用于拟合后的断言。"""
import inspect
import json
import unittest
from pathlib import Path

import numpy as np
from held_observation_v1.geometry import sample
from pose_identifiability_v1.candidate import fit, observed_inliers

PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / "visibility_boundary_v2/evidence/remote"
TRUTH = PROJECT / "visibility_calibration_v1/evidence/remote/phases/before_release/private_truth.json"


def cloud(index):
    with np.load(DATA / f"view_{index}/clouds.npz") as arrays:
        return sample(arrays["noise_0"])


class CandidateTests(unittest.TestCase):
    def test_known_plateau_recovers_without_truth_input(self):
        actual = fit(cloud(3))
        truth = json.loads(TRUTH.read_text(encoding="utf-8"))
        self.assertLess(actual["condition"], 1e4)
        self.assertLessEqual(np.linalg.norm(np.asarray(actual["center"]) - truth["center"]), .010)
        self.assertLessEqual(actual["p95_m"], .006)

    def test_neighbor_good_view_remains_accurate(self):
        actual = fit(cloud(2))
        truth = json.loads(TRUTH.read_text(encoding="utf-8"))
        self.assertLess(actual["condition"], 1e4)
        self.assertLessEqual(np.linalg.norm(np.asarray(actual["center"]) - truth["center"]), .010)

    def test_no_truth_or_camera_arguments(self):
        self.assertEqual(["points"], list(inspect.signature(fit).parameters))

    def test_plane_still_rejected(self):
        x, y = np.meshgrid(np.linspace(-.05, .05, 20), np.linspace(-.02, .02, 20))
        with self.assertRaises(ValueError):
            fit(np.column_stack((x.ravel(), y.ravel(), np.zeros(x.size))))

    def test_nonfinite_observations_rejected(self):
        with self.assertRaises(ValueError):
            fit(np.full((200, 3), np.nan))

    def test_filter_keeps_raw_cloud_unchanged_and_removes_few_points(self):
        points = cloud(3)
        original = points.copy()
        filtered, record = observed_inliers(points)
        np.testing.assert_array_equal(original, points)
        self.assertGreater(record["removed_points"], 0)
        self.assertLessEqual(record["removed_points"], .05 * len(points))
        self.assertEqual(record["kept_points"], len(filtered))

    def test_excessive_isolation_is_rejected(self):
        points = cloud(2)
        isolated = np.column_stack((np.arange(100) + 10., np.zeros(100), np.zeros(100)))
        with self.assertRaisesRegex(ValueError, "excessive_isolation"):
            observed_inliers(np.vstack((points, isolated)))


if __name__ == "__main__":
    unittest.main()
