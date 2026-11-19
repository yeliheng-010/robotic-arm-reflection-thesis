import copy
import json
import unittest
from boundary import build_request
from prompts import messages


def fixture():
    parameters = dict(replan=False, reground=False, lift_height=.35, time_scale=1.,
                      grasp_offset=[0., 0., 0.], place_offset=[0., 0., 0.], candidate_index=0)
    step = dict(index=1, state=dict(parameters=parameters, profile='original'), success=False,
                feedback={'error_type': 'object_dropped', 'message': 'HIDDEN_DIAGNOSIS'})
    ledger = dict(item=dict(source='RedBlock', destination='BlueBin', seed=961103), steps=[step])
    record = dict(parameters=parameters, diagnostics=dict(action='move_to_point',
                  motion_segment='lift', commanded_tcp_xyz=[1., .5, 1.], available_candidate_count=3))
    return ledger, record


class BoundaryTests(unittest.TestCase):
    def test_hidden_information_does_not_change_request(self):
        ledger, record = fixture()
        before = build_request(ledger, record)
        changed, raw = copy.deepcopy(ledger), copy.deepcopy(record)
        changed['item'].update(seed=999, fault='SECRET_CAUSE')
        changed['steps'][0]['feedback'] = {'error_type': 'collision', 'message': 'SECRET_CAUSE'}
        raw.update(error={'message': 'SECRET_CAUSE'}, evaluation={'position': [999, 999, 999]},
                   candidate_trace={'initial_qpos': [999]}, visual={'reason': 'SECRET_CAUSE'})
        raw['diagnostics']['contact_bounds_world'] = ['SECRET_CAUSE']
        self.assertEqual(before, build_request(changed, raw))
        self.assertNotIn('HIDDEN_DIAGNOSIS', json.dumps(before))

    def test_missing_sensing_is_not_fabricated(self):
        ledger, record = fixture()
        record['diagnostics'] = {}
        request = build_request(ledger, record)
        self.assertEqual('not_attached', request['sensing_status']['rgb'])
        self.assertEqual(['parameters'], [row['field'] for row in request['evidence']])

    def test_exhausted_ledger_has_only_stop(self):
        ledger, record = fixture()
        first = ledger['steps'][0]
        ledger['steps'] = [dict(first, index=i) for i in (1, 2, 3)]
        request = build_request(ledger, record, supported=('RETRY', 'OBSERVE'), observations_remaining=2)
        self.assertEqual(0, request['budget']['executions_remaining'])
        self.assertEqual(['STOP'], [row['id'] for row in request['actions']])

    def test_unwired_capabilities_not_advertised(self):
        ledger, record = fixture()
        request = build_request(ledger, record)
        self.assertEqual(['STOP'], [row['id'] for row in request['actions']])

    def test_mismatched_execution_or_bad_budget_rejected(self):
        ledger, record = fixture()
        raw = copy.deepcopy(record)
        raw['parameters']['time_scale'] = 2.
        with self.assertRaises(ValueError):
            build_request(ledger, raw)
        for count in (-1, 3, True):
            with self.assertRaises(ValueError):
                build_request(ledger, record, observations_remaining=count)

    def test_command_metadata_cannot_carry_free_text_diagnosis(self):
        ledger, record = fixture()
        record['diagnostics']['action'] = 'SECRET_CAUSE'
        with self.assertRaises(ValueError):
            build_request(ledger, record)

    def test_comparison_methods_share_identical_visible_input(self):
        ledger, record = fixture()
        request = build_request(ledger, record, supported=('RETRY', 'OBSERVE'), observations_remaining=1)
        self.assertEqual(messages(request, mode='direct')[1], messages(request, mode='diagnostic')[1])

    def test_menu_is_independent_of_error_class(self):
        ledger, record = fixture()
        supported = ('RETRY', 'OBSERVE', 'SET_TIME_SCALE', 'SET_GRASP_OFFSET', 'SELECT_GRASP')
        before = build_request(ledger, record, supported=supported, observations_remaining=1)
        ledger['steps'][0]['feedback']['error_type'] = 'collision'
        self.assertEqual(before, build_request(ledger, record, supported=supported, observations_remaining=1))
        self.assertEqual(6, len(before['actions']))
        self.assertIn('value', next(a for a in before['actions'] if a['id']=='SET_TIME_SCALE')['args_spec'])

    def test_boolean_attempt_and_execution_after_success_rejected(self):
        ledger, record = fixture()
        ledger['steps'][0]['index'] = True
        with self.assertRaises(ValueError):
            build_request(ledger, record)
        ledger['steps'][0].update(index=1, success=True)
        ledger['steps'].append(dict(ledger['steps'][0], index=2, success=False))
        with self.assertRaises(ValueError):
            build_request(ledger, record)


if __name__ == '__main__':
    unittest.main()
