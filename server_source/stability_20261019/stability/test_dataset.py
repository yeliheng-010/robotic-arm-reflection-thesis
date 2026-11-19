import copy
import json
import unittest
from reflection.reflector import Parameters
from stability.dataset import examples


class DatasetTests(unittest.TestCase):
    def setUp(self):
        params = json.loads(json.dumps(Parameters().to_dict()))
        changes = {'lift_height': .45}
        answer = {'cause': 'observed contact during transport', 'changes': changes, 'source': 'llm'}
        error = {'error_type': 'collision', 'message': 'contact', 'evidence': {}}
        first = {'attempt': 1, 'accepted': False, 'physical_success': False,
                 'parameters': params, 'error': error, 'reflection': answer}
        second = {'attempt': 2, 'accepted': True, 'physical_success': True,
                  'parameters': dict(params, **changes), 'error': None,
                  'candidate_trace': {'returned': [[0]]}}
        self.result = {'source': 'RedBlock', 'destination': 'BlueBin', 'seed': 1,
            'fault': 'collision', 'persistent_fault': True, 'records': [first, second]}
        self.retry = {'success': False, 'records': [dict(accepted=False)]}
        response = json.dumps({k: answer[k] for k in ('cause', 'changes')})
        self.events = [{'messages': [{'role': 'system', 'content': 'original prompt'},
            {'role': 'user', 'content': json.dumps({'parameters': params, 'error': error})}],
            'response': {'text': response, 'model': 'frozen_teacher'}, 'parsed': answer}]

    def export(self):
        return examples(self.result, self.retry, self.events, task_id='x', split='train')

    def test_preserves_actual_prompt_and_answer(self):
        row = self.export()[0]
        self.assertEqual(self.events[0]['messages'], row['messages'][:-1])
        self.assertEqual(self.events[0]['response']['text'], row['messages'][-1]['content'])

    def test_excludes_rule_and_natural_recovery(self):
        self.result['records'][0]['reflection']['source'] = 'rule'
        self.assertEqual([], self.export())
        self.result['records'][0]['reflection']['source'] = 'llm'
        self.retry['success'] = True
        self.assertEqual([], self.export())

    def test_rejects_executed_parameter_mismatch(self):
        self.result['records'][1]['parameters']['lift_height'] = .4
        with self.assertRaises(AssertionError):
            self.export()

    def test_rejects_reconstructed_or_altered_teacher_output(self):
        self.events[0]['response']['text'] = '{"cause":"fake","changes":{"lift_height":0.45}}'
        with self.assertRaises(AssertionError):
            self.export()

    def test_excludes_nonpersistent_faults(self):
        self.result['fault'] = 'planning'
        self.assertEqual([], self.export())

    def test_live_tuple_parameters_match_json_request(self):
        self.result['records'][0]['parameters'] = Parameters().to_dict()
        self.assertEqual(1, len(self.export()))

    def test_excludes_silently_clamped_candidate_index(self):
        self.result['records'][0]['reflection']['changes']['candidate_index'] = 4
        self.result['records'][1]['parameters']['candidate_index'] = 4
        self.events[0]['parsed'] = self.result['records'][0]['reflection']
        self.events[0]['response']['text'] = json.dumps({k: self.events[0]['parsed'][k]
                                                      for k in ('cause', 'changes')})
        self.assertEqual([], self.export())


if __name__ == '__main__':
    unittest.main()

