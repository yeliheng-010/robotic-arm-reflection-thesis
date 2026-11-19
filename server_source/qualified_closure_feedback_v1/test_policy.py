import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from qualified_closure_feedback_v1 import policy, budget
from qualified_model_v1.common import save


class PolicyTests(unittest.TestCase):
    def test_closure_feedback_is_only_status_and_stage(self):
        action = dict(id='PROPOSE_GRASP', args={})
        row = policy.entry(action, 'gripper_closure')
        self.assertEqual(dict(action=action, feedback=dict(status='rejected', stage='gripper_closure')), row)
        with self.assertRaises(ValueError):
            policy.entry(action, 'private_tray_location')

    def test_request_keeps_observation_actions_image_and_no_private_fields(self):
        body = dict(observation={'points': [[1, 2, 3]]}, actions=['STOP'], budget={}, history=[])
        original = dict(image='qualified.png', messages=[dict(content='system'), dict(content=json.dumps(body))])
        context = dict(original=original, geometry={k: [] for k in policy.GEOMETRY_KEYS}, grounding={'task': 'place'})
        history = [policy.entry(dict(id='PROPOSE_GRASP', args={}), 'gripper_closure')]
        request = policy.request(context, history, remaining=2)
        parsed = json.loads(request['messages'][1]['content'])
        self.assertEqual(body['observation'], parsed['observation'])
        self.assertEqual(body['actions'], parsed['actions'])
        self.assertEqual('qualified.png', request['image'])
        self.assertEqual(history, parsed['history'])
        self.assertEqual(2, parsed['budget']['decisions'])
        history[0]['private_contacts'] = [1, 2, 3]
        with self.assertRaises(ValueError):
            policy.request(context, history, remaining=2)

    def test_repeat_stop_invalid_do_not_get_extra_draw(self):
        action = dict(id='PROPOSE_GRASP', args={})
        self.assertEqual('repeated_rejected_action', policy.permitted(action, [policy.entry(action, 'gripper_closure')]))
        self.assertEqual('model_stopped', policy.permitted(dict(id='STOP'), []))

    def test_budget_reservation_is_exclusive_bounded_and_requires_previous_rejection(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(budget, 'RUN', root), patch.object(budget, 'verify', lambda: {}):
                with self.assertRaises(ValueError):
                    budget.reserve(3)
                with self.assertRaises(FileNotFoundError):
                    budget.reserve(2)
                save(root / 'decision_1/request.json', {'input': 'fixed'})
                budget.reserve(1)
                with self.assertRaises(FileExistsError):
                    budget.reserve(1)
                save(root / 'decision_1/result.json', {'status': 'model_stopped'})
                with self.assertRaises(ValueError):
                    budget.reserve(2)


if __name__ == '__main__':
    unittest.main()
