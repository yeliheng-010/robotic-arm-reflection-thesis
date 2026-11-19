"""提前失败必须可重放；不能把截断轨迹或伪造异常当作合法退出。"""
import copy
import unittest
from reflection.errors import ErrorReport, ErrorType
from reflection.reflector import Parameters
from stability.recovery_audit import validate_early_exit


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        report = ErrorReport(ErrorType.PLACEMENT_OFFSET, 'Outside container',
                             {'placement_residual_xy': [.30, 0]}, detector='test')
        record = dict(attempt=1, accepted=False, parameters=Parameters().to_dict(),
            error=report.to_dict(), reflection_error='place_offset components must be finite within 0.25 m')
        self.expert = dict(method='reflection', reflector='RuleReflector', persistent_fault=True,
            retry_protocol='restore_same_initial_scene_each_attempt', success=False, attempts=1,
            records=[record])
        records = [dict(attempt=i, accepted=False, parameters=Parameters().to_dict()) for i in range(1, 4)]
        self.retry = dict(self.expert, method='retry', reflector=None, attempts=3, records=records)
        self.summary = dict(paired=True, calls=1, invalid=1, samples=[])

    def test_accepts_replayed_invalid_correction_without_mutation(self):
        before = copy.deepcopy(self.expert)
        validate_early_exit(self.expert, self.retry, self.summary)
        self.assertEqual(before, self.expert)

    def test_rejects_forged_error_or_usable_correction(self):
        for field in ('reflection_error', 'error'):
            expert = copy.deepcopy(self.expert)
            if field == 'reflection_error':
                expert['records'][-1][field] = 'invented error'
            else:
                expert['records'][-1][field]['evidence']['placement_residual_xy'] = [.10, 0]
            with self.assertRaises(AssertionError):
                validate_early_exit(expert, self.retry, self.summary)

    def test_rejects_short_retry_and_nonempty_labels(self):
        retry = dict(self.retry, records=self.retry['records'][:2], attempts=2)
        with self.assertRaises(AssertionError):
            validate_early_exit(self.expert, retry, self.summary)
        with self.assertRaises(AssertionError):
            validate_early_exit(self.expert, self.retry, dict(self.summary, samples=[{}]))

    def test_rejects_bad_counts_and_llm_source(self):
        with self.assertRaises(AssertionError):
            validate_early_exit(self.expert, self.retry, dict(self.summary, calls=2))
        with self.assertRaises(AssertionError):
            validate_early_exit(dict(self.expert, reflector='LLMReflector'), self.retry, self.summary)


if __name__ == '__main__':
    unittest.main()
