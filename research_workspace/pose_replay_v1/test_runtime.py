import unittest
from unittest.mock import patch
import numpy as np
from pose_replay_v1 import runtime


def fitted(condition=50.):
    return dict(center=[0., 0., 0.], axis=[1., 0., 0.], radius=.025,
                half_length=.055, p95_m=.002, converged=True, condition=condition)


class RuntimeTests(unittest.TestCase):
    def test_single_records_filter_failure(self):
        with patch.object(runtime, "fit", side_effect=ValueError("excessive_isolation")):
            result = runtime.single(np.ones((200, 3)))
        self.assertIsNone(result["fit"])
        self.assertFalse(result["quality_passed"])
        self.assertEqual("excessive_isolation", result["failure"])

    def test_pair_never_ignores_failed_single(self):
        values = [dict(fit=None), dict(fit=fitted())]
        with patch.object(runtime, "fit") as solver:
            result = runtime.pair([np.ones((200, 3))]*2, values)
        solver.assert_not_called()
        self.assertFalse(result["quality_passed"])

    def test_pair_preserves_single_condition_gate(self):
        values = [dict(fit=fitted(1e8)), dict(fit=fitted())]
        with patch.object(runtime, "fit", return_value=fitted()):
            result = runtime.pair([np.ones((200, 3))]*2, values)
        self.assertFalse(result["quality_passed"])

    def test_pair_preserves_disagreement_gate(self):
        displaced = fitted()
        displaced["center"] = [.05, 0., 0.]
        with patch.object(runtime, "fit", return_value=fitted()):
            result = runtime.pair([np.ones((200, 3))]*2,
                                  [dict(fit=displaced), dict(fit=fitted())])
        self.assertFalse(result["quality_passed"])


if __name__ == "__main__":
    unittest.main()
