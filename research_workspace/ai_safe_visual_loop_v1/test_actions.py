import unittest
from copy import deepcopy
import action_check
from sv_actions import check, choose, validate


def request():
    return dict(actions=[dict(id=k) for k in ('STOP', 'OBSERVE', 'SET_GRASP_OFFSET', 'SET_TIME_SCALE', 'RETRY')],
        budget=dict(executions_remaining=2, observations_remaining=2),
        state=dict(grasp_offset=[0., 0., 0.], time_scale=1.5),
        evidence=[dict(field='rgbd_surface_observations', value=[dict(observed={'source': {'status':'ok'}})])])


class ActionTests(unittest.TestCase):
    def test_new_bound_and_restore_old_interface(self):
        action = dict(id='SET_GRASP_OFFSET', args=dict(delta_m=[0., 0., -.03]))
        check(action, request())
        self.assertEqual(.01, action_check.MAX_DELTA_M)
        with self.assertRaises(ValueError):
            action_check.check(action, request())

    def test_single_axis_finite_and_accumulated_bound(self):
        for delta in ([.01, 0., -.02], [0., 0., -.031], [0., 0., float('nan')]):
            with self.assertRaises(ValueError):
                check(dict(id='SET_GRASP_OFFSET', args=dict(delta_m=delta)), request())
        value = request()
        value['state']['grasp_offset'] = [0., 0., -.03]
        with self.assertRaises(ValueError):
            check(dict(id='SET_GRASP_OFFSET', args=dict(delta_m=[0., 0., -.03])), value)

    def test_rule_uses_public_observation_and_command_only(self):
        value = request()
        self.assertEqual('SET_GRASP_OFFSET', choose(value)['id'])
        value['state']['grasp_offset'] = [0., 0., -.03]
        self.assertEqual('SET_TIME_SCALE', choose(value)['id'])
        value['evidence'][0]['value'][0]['observed']['source']['status'] = 'insufficient_visible_depth'
        self.assertEqual('OBSERVE', choose(value)['id'])

    def test_parser_and_budget(self):
        response = dict(finish_reason='stop', text='{"action":{"id":"SET_GRASP_OFFSET","args":{"delta_m":[0,0,-0.03]}}}')
        self.assertTrue(validate(response, request(), mode='direct')['valid'])
        value = request()
        value['budget']['executions_remaining'] = 0
        self.assertFalse(validate(response, value, mode='direct')['valid'])
        self.assertEqual(.01, action_check.MAX_DELTA_M)
