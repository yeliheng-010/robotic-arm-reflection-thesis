import importlib.util
import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        name = 'qualified_prompt_checkpoint_v1.protocol'
        self.assertIsNotNone(importlib.util.find_spec(name), 'missing one-call protocol implementation')
        self.protocol = __import__(name, fromlist=['protocol'])

    def fixture(self):
        project = Path(__file__).resolve().parent.parent
        old = project / 'qualified_closure_feedback_v1/run/decision_2/request.json'
        draft = Path(__file__).resolve().parent / 'B_checkpoint.json'
        return self.protocol.read(old), self.protocol.read(draft)

    def test_only_checkpoint_and_zero_planning_budget_change(self):
        original, draft = self.fixture()
        saved = deepcopy(original)
        result = self.protocol.build_request(original, draft)
        body = json.loads(result['messages'][1]['content'])
        before = json.loads(original['messages'][1]['content'])
        self.assertEqual(dict(decisions=1, planning=0, observations=0), body['budget'])
        checkpoint = body.pop('decision_checkpoint')
        self.assertEqual(before['history'][-1], checkpoint['latest_public_rejection'])
        body['budget'] = before['budget']
        self.assertEqual(before, body)
        result['messages'][1]['content'] = original['messages'][1]['content']
        self.assertEqual(original, result)
        self.assertEqual(saved, original)

    def test_tampered_draft_observation_or_private_feedback_is_rejected(self):
        original, draft = self.fixture()
        for key in ('observation', 'decision_checkpoint'):
            tampered = deepcopy(draft)
            body = json.loads(tampered['request']['messages'][1]['content'])
            body[key]['private_contact'] = [1, 2, 3]
            tampered['request']['messages'][1]['content'] = json.dumps(body)
            with self.assertRaises(ValueError):
                self.protocol.build_request(original, tampered)

    def test_exclusive_claim_allows_only_one_concurrent_reservation(self):
        with TemporaryDirectory() as name:
            root = Path(name)
            self.protocol.save(root / 'request.json', {'fixed': True})
            request = root / 'request.json'
            self.protocol.save(root / 'manifest.json', dict(
                identities={str(request): self.protocol.sha(request)},
                max_model_calls=1, max_planning=0, max_physical=0, max_training=0))
            def attempt(_):
                try:
                    self.protocol.reserve(root)
                    return True
                except FileExistsError:
                    return False
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(1, sum(pool.map(attempt, (1, 2))))
            self.assertEqual(1, self.protocol.read(root / 'model_claim.json')['consumed'])
            with self.assertRaises(FileExistsError):
                self.protocol.reserve(root)

    def test_changed_registered_input_prevents_reservation(self):
        with TemporaryDirectory() as name:
            root = Path(name)
            self.protocol.save(root / 'request.json', {'fixed': True})
            request = root / 'request.json'
            self.protocol.save(root / 'manifest.json', dict(
                identities={str(request): 'incorrect'},
                max_model_calls=1, max_planning=0, max_physical=0, max_training=0))
            with self.assertRaises(ValueError):
                self.protocol.reserve(root)
            self.assertFalse((root / 'model_claim.json').exists())

    def test_repeat_stop_and_novel_are_distinguished_without_planning(self):
        original, _ = self.fixture()
        history = json.loads(original['messages'][1]['content'])['history']
        novel = dict(id='PROPOSE_GRASP', args=dict(region='center', depth_mm=15,
                    tilt_deg=0, azimuth_deg=0, symmetry_deg=0))
        cases = [(history[-1]['action'], 'repeated_rejected_action'),
                 (dict(id='STOP', args={}), 'model_stopped'), (novel, 'novel_action_unchecked')]
        for action, status in cases:
            response = dict(finish_reason='stop', text=json.dumps(dict(action=action)))
            result = self.protocol.classify(response, history)
            self.assertTrue(result['valid'])
            self.assertEqual(status, result['status'])
            self.assertEqual(action, result['action'])

    def test_invalid_json_and_non_eos_stop_without_repair(self):
        bad = [dict(finish_reason='length', text='{}'),
               dict(finish_reason='stop', text='{"action":{},"action":{}}'),
               dict(finish_reason='stop', text='{"action":{"id":"STOP","args":{"x":1}}}')]
        for response in bad:
            result = self.protocol.classify(response, [])
            self.assertFalse(result['valid'])
            self.assertEqual('invalid', result['status'])
            self.assertIsNone(result['action'])


if __name__ == '__main__':
    unittest.main()
