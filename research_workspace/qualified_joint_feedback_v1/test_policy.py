import json
import unittest
from copy import deepcopy
from qualified_joint_feedback_v1 import policy


def report(grasp=True, release=1, passed=False):
    return dict(plan=dict(endpoints=dict(grasps=[dict(ok=grasp)], passing=release)),
        strict=dict(passed=passed))


class JointFeedbackTests(unittest.TestCase):
    def test_stage_distinguishes_grasp_from_release(self):
        self.assertEqual('grasp_endpoint', policy.outcome(report(grasp=False, release=0))['stage'])
        self.assertEqual('place_endpoint', policy.outcome(report(release=0))['stage'])

    def test_full_path_and_return_home_stay_blocked(self):
        value = report()
        self.assertEqual('path', policy.outcome(value)['stage'])
        value['strict']['return_home'] = dict(selected=None)
        self.assertEqual('return_home', policy.outcome(value)['stage'])
        self.assertEqual('ready', policy.outcome(report(passed=True))['status'])

    def test_private_diagnostics_never_enter_feedback(self):
        value = report(release=0)
        value['plan']['private_collision'] = 'secret_body_and_pose'
        public = policy.outcome(value)
        entry = policy.entry(dict(id='PROPOSE_GRASP', args={}), public['stage'])
        self.assertEqual({'status', 'stage'}, set(entry['feedback']))
        self.assertNotIn('secret', json.dumps(entry))
        with self.assertRaises(ValueError):
            policy.entry({}, 'collision_with_secret_body')

    def test_observation_choices_preserved_and_geometry_whitelisted(self):
        body = dict(observation={'points': [[1, 2, 3]]}, actions=['STOP'], history=[], budget={})
        original = dict(image='qualified.png', messages=[dict(content='system'), dict(content=json.dumps(body))])
        geometry = {key: [1.23456789] for key in policy.GEOMETRY_KEYS}
        geometry['private_truth'] = 'must_not_leak'
        saved = deepcopy(original)
        request = policy.request(original, [], remaining=2, geometry=geometry, grounding=dict(task='place'))
        actual = json.loads(request['messages'][1]['content'])
        self.assertEqual(body['observation'], actual['observation'])
        self.assertEqual(body['actions'], actual['actions'])
        self.assertEqual(saved, original)
        self.assertEqual(set(policy.GEOMETRY_KEYS), set(actual['observed_placement']))
        self.assertEqual([1.23457], actual['observed_placement']['centers'])
        self.assertEqual(dict(decisions=2, planning=2, observations=0), actual['budget'])

    def test_stop_repeat_and_other_action_do_not_plan(self):
        action = dict(id='PROPOSE_GRASP', args={})
        history = [policy.entry(action, 'place_endpoint')]
        self.assertEqual('repeated_rejected_action', policy.permitted(action, history))
        self.assertEqual('model_stopped', policy.permitted(dict(id='STOP'), history))
        self.assertEqual('unsupported_action', policy.permitted(dict(id='OBSERVE'), history))


if __name__ == '__main__':
    unittest.main()
