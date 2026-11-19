import json
from pathlib import Path
import tempfile
import unittest

from reflection.reflector import Parameters
from training.overnight.collect import build_plan
from training.overnight.dataset import atomic, finalize, split_examples


class OvernightDataTests(unittest.TestCase):
    def test_plan_has_disjoint_seed_groups_and_early_heldout_tasks(self):
        plan = build_plan(2000)
        self.assertEqual(len(plan), 480)
        self.assertEqual(len({(p['seed'], p['source'], p['destination'], p['fault']) for p in plan}), 480)
        groups = {split: {p['seed'] for p in plan if p['split'] == split}
                  for split in ('train', 'validation', 'test')}
        self.assertFalse(groups['train'] & groups['validation'])
        self.assertFalse(groups['train'] & groups['test'])
        self.assertFalse(groups['test'] & groups['validation'])
        self.assertEqual({p['split'] for p in plan[:4]}, {'train', 'validation', 'test'})

    def test_same_prompt_different_answers_cannot_leak_across_splits(self):
        def row(split, answer):
            return {'messages': [{'role': 'system', 'content': 'rules'},
                                 {'role': 'user', 'content': 'same evidence'},
                                 {'role': 'assistant', 'content': answer}], 'metadata': {'split': split}}
        splits, dropped = split_examples([row('train', 'A'), row('validation', 'B'), row('test', 'C')])
        self.assertEqual({k: len(v) for k, v in splits.items()}, {'train': 0, 'validation': 0, 'test': 1})
        self.assertEqual(dropped, {'validation': 1, 'train': 1})

    def test_finalizer_filters_failed_execution_and_keeps_failure_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = build_plan(2000)[:4]
            atomic(root/'manifest.json', {'teacher': {'model': 'test-base'}, 'config': {'deadline': 1}})
            atomic(root/'plan.json', plan)
            p = Parameters()
            for index, task in enumerate(plan):
                result = {**task, 'success': index != 0, 'persistent_fault': False,
                    'records': [
                        {'attempt': 1, 'parameters': p.to_dict(),
                         'error': {'error_type': 'planning', 'message': 'plan invalid'},
                         'reflection': {'source': 'llm', 'cause': 'invalid plan', 'changes': {'replan': True}}},
                        {'attempt': 2, 'parameters': p.updated({'replan': True}).to_dict(),
                         'accepted': index != 0, 'physical_success': index != 0}]}
                atomic(root/'tasks'/f'{index:05d}'/'result.json', result)
            report = finalize(root, 'test')
            self.assertEqual(report['completed_tasks'], 4)
            self.assertEqual(report['successful_tasks'], 3)
            self.assertEqual(sum(report['samples'].values()), 3)
            self.assertFalse(report['ready_for_initial_training'])
            for path in (root/'dataset').glob('*.jsonl'):
                for line in path.read_text().splitlines():
                    row = json.loads(line)
                    self.assertEqual(row['metadata']['prompt_format'], 'text-reflection-v2')
                    self.assertIn('world XYZ', row['messages'][0]['content'])
            self.assertTrue((root/'MORNING_REPORT.md').exists())


if __name__ == '__main__':
    unittest.main()
