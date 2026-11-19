"""专家监督必须真实重放规则并匹配执行，禁止混淆来源。"""
import copy
import json
import unittest
from reflection.reflector import Parameters
from stability.expert_dataset import examples


class ExpertTests(unittest.TestCase):
    def setUp(self):
        params = json.loads(json.dumps(Parameters().to_dict()))
        error = {'error_type': 'collision', 'message': 'Unexpected contact',
                 'evidence': {}, 'detector': 'mujoco_monitor'}
        first = {'attempt': 1, 'accepted': False, 'physical_success': False, 'error': error,
            'parameters': params, 'candidate_trace': {'returned': [[0]]},
            'reflection': {'cause': 'Unexpected contact', 'changes': {'lift_height': .45}, 'source': 'rule'}}
        second = {'attempt': 2, 'accepted': True, 'physical_success': True, 'error': None,
                  'parameters': dict(params, lift_height=.45), 'candidate_trace': {'returned': [[0]]}}
        self.result = {'source': 'RedBlock', 'destination': 'BlueBin', 'instruction': '搬运红块',
            'seed': 6000, 'fault': 'collision', 'persistent_fault': True, 'records': [first, second]}
        self.retry = {'success': False, 'records': [{'accepted': False}]}

    def export(self):
        return examples(self.result, self.retry, task_id='00000', split='train')

    def test_truthful_source_and_no_hidden_fault_in_prompt(self):
        before = copy.deepcopy(self.result)
        row = self.export()[0]
        self.assertEqual('rule_expert', row['metadata']['teacher_source'])
        self.assertIsNone(row['metadata']['model'])
        self.assertNotIn('fault', json.loads(row['messages'][1]['content']))
        self.assertEqual(before, self.result)

    def test_rejects_forged_rule_and_relabelled_llm(self):
        self.result['records'][0]['reflection']['source'] = 'llm'
        with self.assertRaises(ValueError):
            self.export()
        self.result['records'][0]['reflection']['source'] = 'rule'
        self.result['records'][0]['reflection']['cause'] = 'fabricated explanation'
        with self.assertRaises(AssertionError):
            self.export()

    def test_rejects_execution_mismatch_and_natural_recovery(self):
        self.result['records'][1]['parameters']['lift_height'] = .4
        with self.assertRaises(AssertionError):
            self.export()
        self.retry['success'] = True
        self.assertEqual([], self.export())

    def test_excludes_unverified_success(self):
        self.result['records'][1]['physical_success'] = False
        self.assertEqual([], self.export())


if __name__ == '__main__':
    unittest.main()
