import json
import unittest
from decision import parse


def request():
    return dict(evidence=[dict(id='e1', field='action', value='move_to_point')],
                state=dict(grasp_offset=[0., 0., 0.]),
                budget=dict(executions_remaining=2, observations_remaining=1),
                actions=[dict(id='STOP'), dict(id='RETRY'), dict(id='OBSERVE'),
                         dict(id='SET_TIME_SCALE'), dict(id='SET_GRASP_OFFSET'),
                         dict(id='SELECT_GRASP', count=3)])


def answer(action='RETRY', args=None):
    return dict(action=dict(id=action, args=args or {}),
                assessment=dict(hypotheses=[], uncertainty='现有信息不足以确定原因'),
                expected_observation='下一次观测用于区分假设，不保证成功')


class DecisionTests(unittest.TestCase):
    def test_invalid_action_never_falls_back(self):
        with self.assertRaises(ValueError):
            parse(json.dumps(answer('CHANGE_FRICTION')), request(), mode='diagnostic')

    def test_unavailable_and_exhausted_actions_rejected(self):
        value = request()
        value['budget']['executions_remaining'] = 0
        for action in ('RETRY', 'OBSERVE'):
            with self.assertRaises(ValueError):
                parse(json.dumps(answer(action)), value, mode='diagnostic')
        value = request()
        value['actions'] = [dict(id='STOP')]
        with self.assertRaises(ValueError):
            parse(json.dumps(answer('RETRY')), value, mode='diagnostic')

    def test_unknown_evidence_reference_rejected(self):
        value = answer()
        value['assessment']['hypotheses'] = [dict(claim='可能发生滑移', evidence_ids=['hidden_truth'])]
        with self.assertRaises(ValueError):
            parse(json.dumps(value), request(), mode='diagnostic')

    def test_duplicate_keys_nonfinite_and_extra_fields_rejected(self):
        bad = ['{"action":{},"action":{}}', '{"action":NaN}',
               json.dumps(dict(answer(), override_safety=True))]
        for text in bad:
            with self.assertRaises(ValueError):
                parse(text, request(), mode='diagnostic')

    def test_parameter_bounds_and_exact_args(self):
        for action, args in [('SET_TIME_SCALE', {'value': 99}),
                             ('SET_GRASP_OFFSET', {'delta_m': [.01, .01, 0]}),
                             ('SELECT_GRASP', {'index': 3}), ('RETRY', {'force': 100})]:
            with self.assertRaises(ValueError):
                parse(json.dumps(answer(action, args)), request(), mode='diagnostic')

    def test_uncertain_assessment_and_valid_choice_preserved(self):
        value = answer('SET_TIME_SCALE', {'value': 1.5})
        self.assertEqual(value, parse(json.dumps(value), request(), mode='diagnostic'))

    def test_direct_and_diagnostic_accept_same_action(self):
        value = answer('OBSERVE')
        direct = dict(action=value['action'])
        self.assertEqual(direct, parse(json.dumps(direct), request(), mode='direct'))
        self.assertEqual(value, parse(json.dumps(value), request(), mode='diagnostic'))

    def test_valid_parameter_proposals_are_not_replaced(self):
        for action, args in [('SET_GRASP_OFFSET', {'delta_m': [.01, 0, 0]}),
                             ('SELECT_GRASP', {'index': 2})]:
            value = answer(action, args)
            self.assertEqual(value, parse(json.dumps(value), request(), mode='diagnostic'))

    def test_offset_absolute_limit_and_observation_budget(self):
        value = request()
        value['state']['grasp_offset'] = [.25, 0, 0]
        with self.assertRaises(ValueError):
            parse(json.dumps(answer('SET_GRASP_OFFSET', {'delta_m': [.01, 0, 0]})), value, mode='diagnostic')
        value['budget']['observations_remaining'] = 0
        with self.assertRaises(ValueError):
            parse(json.dumps(answer('OBSERVE')), value, mode='diagnostic')


if __name__ == '__main__':
    unittest.main()
