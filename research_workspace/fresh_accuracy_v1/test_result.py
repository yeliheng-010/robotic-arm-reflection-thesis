"""未知和拒绝不能被统计成失败；只有成对审计结果能比较。"""
import unittest
from fa_result import classify, totals


class ResultTests(unittest.TestCase):
    def test_rejection_preserves_denominator(self):
        result = totals([dict(status='camera_rejected'), dict(status='geometry_rejected')])
        for row in result.values():
            self.assertEqual(2, row['registered'])
            self.assertEqual(2, row['rejected'])
            self.assertEqual(0, row['failure'])

    def test_unpaired_success_is_unknown(self):
        row = dict(status='input_pair_error', policies=dict(improved=dict(passed=True, success=True)))
        self.assertEqual('unknown', classify(row, 'improved'))

    def test_audit_failure_and_missing_result_are_unknown(self):
        for audit in ({}, dict(passed=False, success=False), dict(passed=True)):
            row = dict(status='paired', policies=dict(original=audit))
            self.assertEqual('unknown', classify(row, 'original'))

    def test_audited_boolean_outcomes(self):
        row = dict(status='paired', policies=dict(original=dict(passed=True, success=False),
                                                  improved=dict(passed=True, success=True)))
        result = totals([row])
        self.assertEqual(1, result['original']['failure'])
        self.assertEqual(1, result['improved']['success'])


if __name__ == '__main__':
    unittest.main()
