import json
import unittest
from qualified_feedback_v1.policy import entry, request, permitted


class FeedbackTests(unittest.TestCase):
    def test_public_feedback_has_no_diagnosis(self):
        action = dict(id='PROPOSE_GRASP', args=dict(region='center'))
        row = entry(action)
        self.assertEqual({'action', 'feedback'}, set(row))
        self.assertEqual(dict(status='rejected', stage='grasp_endpoint'), row['feedback'])
        action['args']['region'] = 'changed'
        self.assertEqual('center', row['action']['args']['region'])

    def test_same_observation_and_choices(self):
        raw = dict(observation=dict(points=[[1, 2, 3]]), actions=['STOP'], history=[], budget={})
        original = dict(image='qualified.png', messages=[dict(content='system'), dict(content=json.dumps(raw))])
        actual = request(original, [], remaining=2)
        body = json.loads(actual['messages'][1]['content'])
        self.assertEqual(raw['observation'], body['observation'])
        self.assertEqual(raw['actions'], body['actions'])
        self.assertEqual('qualified.png', actual['image'])
        self.assertEqual(0, body['budget']['observations'])

    def test_stop_and_duplicate_are_not_executed(self):
        action = dict(id='PROPOSE_GRASP', args={})
        self.assertEqual('repeated_rejected_action', permitted(action, [entry(action)]))
        self.assertEqual('model_stopped', permitted(dict(id='STOP', args={}), []))
        self.assertEqual('proposal', permitted(action, []))


if __name__ == '__main__':
    unittest.main()
