"""候选ID评价不能容忍额外解释、重复键或未知动作。"""
import unittest
from runtime import validate_text
from stability.sft_data import epoch_groups

MESSAGES = [dict(role='system',content='select'),
            dict(role='user',content='{"candidates":[{"id":"a"},{"id":"b"}]}'),
            dict(role='assistant',content='{"action_id":"a"}')]


class MetricTests(unittest.TestCase):
    def test_valid_alternative_is_not_reference_match(self):
        result = validate_text('{"action_id":"b"}',MESSAGES)
        self.assertTrue(result['candidate_valid'])
        self.assertFalse(result['target_match'])

    def test_unknown_id_is_invalid(self):
        self.assertFalse(validate_text('{"action_id":"unknown"}',MESSAGES)['candidate_valid'])

    def test_duplicate_or_extra_field_rejected(self):
        for value in ('{"action_id":"a","action_id":"b"}',
                      '{"action_id":"a","reason":"x"}', '```json\n{"action_id":"a"}\n```'):
            self.assertFalse(validate_text(value,MESSAGES)['candidate_valid'])

    def test_tail_batch_preserved(self):
        groups = epoch_groups(159,accumulation=8,seed=42)
        self.assertEqual(20,len(groups))
        self.assertEqual(7,len(groups[-1]))
        self.assertEqual(list(range(159)),sorted(i for g in groups for i in g))


if __name__=='__main__':
    unittest.main()
