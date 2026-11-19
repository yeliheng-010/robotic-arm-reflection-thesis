"""专家采集的来源、隔离、预算及停止门禁。"""
import copy
from pathlib import Path
import tempfile
import unittest
from stability.expert_audit import validate_raw
from stability.expert_collect import stop_reason
from stability.expert_config import validate_gate
from stability.expert_status import datasets_from


class PipelineTests(unittest.TestCase):
    def row(self, split='train'):
        return {'metadata': {'teacher_source': 'rule_expert', 'model': None,
            'split': split, 'prompt_sha256': 'same', 'source': 'RedBlock', 'destination': 'BlueBin'}}

    def summary(self, rows):
        return {'supervision_source': 'rule_expert', 'samples': rows}

    def test_source_and_split_contamination_rejected(self):
        row = self.row()
        row['metadata']['teacher_source'] = 'llm'
        with self.assertRaises(AssertionError):
            datasets_from([self.summary([row])], stage='batch')
        with self.assertRaises(AssertionError):
            datasets_from([self.summary([self.row('test')])], stage='batch')
        with self.assertRaises(AssertionError):
            datasets_from([self.summary([self.row(), self.row('test')])], stage='pilot')

    def test_duplicate_inputs_do_not_inflate_count(self):
        datasets, duplicates = datasets_from([self.summary([self.row(), self.row()])], stage='batch')
        self.assertEqual(1, duplicates)
        self.assertEqual(1, len(datasets['train']))

    def test_pure_model_gate_cannot_authorize_expert_batch(self):
        config = dict(code={}, expert_code={}, supervision_source='rule_expert', generator='rule')
        with self.assertRaises(AssertionError):
            validate_gate(dict(config, allow_batch=True, supervision_source='llm'), config)
        with self.assertRaises(AssertionError):
            validate_gate(dict(config, allow_batch=False), config)

    def test_stop_file_and_bad_labels_stop_submission(self):
        status = dict(sample_count_gate=False, calls=20, invalid=5, completed_tasks=10)
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual('invalid_rule_rate_above_20_percent', stop_reason(status, Path(folder)))
            (Path(folder)/'STOP').touch()
            self.assertEqual('user_stop_file', stop_reason(status, Path(folder)))

    def test_audit_rejects_truncated_retry_and_forged_counts(self):
        records = [dict(attempt=i, accepted=False, parameters={}) for i in range(1, 4)]
        retry = dict(method='retry', reflector=None, persistent_fault=True, attempts=3,
            retry_protocol='restore_same_initial_scene_each_attempt', success=False, records=records)
        expert = dict(copy.deepcopy(retry), method='reflection')
        summary = dict(paired=True, calls=0, invalid=0)
        validate_raw(expert, retry, summary)
        with self.assertRaises(AssertionError):
            validate_raw(expert, retry, dict(summary, calls=1))
        retry['records'] = retry['records'][:2]
        retry['attempts'] = 2
        with self.assertRaises(AssertionError):
            validate_raw(expert, retry, summary)


if __name__ == '__main__':
    unittest.main()
