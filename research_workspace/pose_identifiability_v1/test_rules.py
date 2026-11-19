import unittest
from pose_identifiability_v1.rules import evaluate_rule


class RuleTests(unittest.TestCase):
    def test_high_visibility_does_not_override_quality(self):
        rows = [dict(visibility=.90, quality_passed=False, accurate=False),
                dict(visibility=.75, quality_passed=True, accurate=True)]
        result = evaluate_rule(rows, .75)
        self.assertEqual(1, result["accepted"])
        self.assertEqual(0, result["false_accepted"])
        self.assertEqual(.5, result["coverage"])

    def test_quality_false_accept_is_counted(self):
        result = evaluate_rule([dict(visibility=.8, quality_passed=True, accurate=False)], .7)
        self.assertEqual(1, result["false_accepted"])
        self.assertEqual(0., result["accepted_accuracy"])

    def test_empty_acceptance_is_not_perfect_accuracy(self):
        result = evaluate_rule([dict(visibility=.2, quality_passed=True, accurate=True)], .7)
        self.assertIsNone(result["accepted_accuracy"])
        self.assertEqual(0., result["coverage"])

    def test_invalid_visibility_is_not_accepted(self):
        rows = [dict(visibility=value, quality_passed=True, accurate=True)
                for value in (float("nan"), float("inf"), -1., 1.1)]
        self.assertEqual(0, evaluate_rule(rows, .7)["accepted"])


if __name__ == "__main__":
    unittest.main()
