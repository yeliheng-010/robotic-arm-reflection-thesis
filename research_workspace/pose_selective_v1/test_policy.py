import unittest
from pose_selective_v1.policy import choose


class PolicyTests(unittest.TestCase):
    def test_original_accepted_is_never_replaced(self):
        self.assertEqual("original", choose(True, True))
        self.assertEqual("original", choose(True, False))

    def test_repair_used_only_after_original_rejection(self):
        self.assertEqual("repaired", choose(False, True))

    def test_both_rejected_stays_rejected(self):
        self.assertIsNone(choose(False, False))

    def test_nonboolean_quality_is_not_approval(self):
        self.assertIsNone(choose("true", float("nan")))


if __name__ == "__main__":
    unittest.main()
