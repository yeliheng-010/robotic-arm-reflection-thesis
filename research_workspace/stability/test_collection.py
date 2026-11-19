import json
from pathlib import Path
import tempfile
import unittest
from concurrent.futures import Future
from unittest.mock import MagicMock, patch
from stability.collection_plan import task_plan
from stability.collection_status import update
from stability.collect import stop_reason, run_pool


class CollectionTests(unittest.TestCase):
    def test_task_families_and_seeds_do_not_cross_splits(self):
        families, seeds, identities = {}, {}, set()
        for task in task_plan('batch'):
            family = (task['source'], task['destination'])
            split = task['split']
            self.assertEqual(split, families.setdefault(family, split))
            self.assertEqual(split, seeds.setdefault(task['seed'], split))
            identity = tuple(sorted(task.items()))
            self.assertNotIn(identity, identities)
            identities.add(identity)

    def test_empty_collection_cannot_start_training(self):
        with tempfile.TemporaryDirectory() as name:
            status = update(Path(name), planned=12)
            self.assertFalse(status['sample_count_gate'])
            self.assertFalse(status['training_started'])
            self.assertEqual(0, status['completed_tasks'])

    def test_service_and_invalid_response_stop_gates(self):
        status = {'sample_count_gate': False, 'service_errors': 2, 'calls': 2, 'invalid': 2}
        self.assertEqual('service_errors_require_review', stop_reason(status, stage='pilot'))
        status.update(service_errors=0, calls=20, invalid=5)
        self.assertEqual('invalid_response_rate_above_20_percent', stop_reason(status, stage='pilot'))

    def test_cross_split_duplicate_inputs_fail_closed(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            for index, split in enumerate(('train', 'test')):
                directory = root/'tasks'/str(index)
                directory.mkdir(parents=True)
                sample = {'metadata': {'split': split, 'prompt_sha256': 'same'}}
                (directory/'summary.json').write_text(json.dumps({'samples': [sample]}))
            with self.assertRaisesRegex(RuntimeError, 'leakage'):
                update(root, planned=2)

    def test_worker_failure_is_persisted_before_raising(self):
        future = Future()
        future.set_exception(RuntimeError('physics failed'))
        pool = MagicMock()
        pool.__enter__.return_value.submit.return_value = future
        with tempfile.TemporaryDirectory() as name, patch('stability.collect.ProcessPoolExecutor', return_value=pool):
            root = Path(name)
            with self.assertRaises(RuntimeError):
                run_pool({'stage': 'pilot', 'plan': [{}]}, root)
            status = json.loads((root/'status.json').read_text())
            self.assertEqual('worker_failure', status.get('stop_reason'))
            self.assertFalse(status['training_started'])


if __name__ == '__main__':
    unittest.main()
