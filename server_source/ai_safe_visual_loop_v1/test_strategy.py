import unittest
from copy import deepcopy
from loopstudy.actions import initial
from test_actions import request
from sv_strategy_actions import check, validate, apply, choose, STRATEGY_ACTION
from sv_strategy_requests import decorate


def bundle(strategy='original'):
    value = request()
    value['execution_semantics'] = {}
    return decorate(dict(request=value), strategy)


class StrategyInterfaceTests(unittest.TestCase):
    def test_modes_share_actions_and_new_parser_accepts_registered_strategy(self):
        value = bundle()
        self.assertEqual(value['direct_messages'][1], value['diagnostic_messages'][1])
        action = dict(id=STRATEGY_ACTION, args=dict(value='observed_top'))
        check(action, value['request'])
        response = dict(finish_reason='stop', text='{"action":{"id":"SET_GRASP_STRATEGY","args":{"value":"observed_top"}}}')
        self.assertTrue(validate(response, value['request'], mode='direct')['valid'])
        self.assertEqual(action, choose(value['request']))

    def test_switch_consumes_execution_and_forbids_top_offset_mix(self):
        value = bundle()['request']
        value['budget']['executions_remaining'] = 0
        action = dict(id=STRATEGY_ACTION, args=dict(value='observed_top'))
        with self.assertRaises(ValueError):
            check(action, value)
        top = bundle('observed_top')['request']
        with self.assertRaises(ValueError):
            check(dict(id='SET_GRASP_OFFSET', args=dict(delta_m=[0,0,-.01])), top)
        with self.assertRaises(ValueError):
            check(action, top)

    def test_transition_resets_offset_without_mutating_previous_state(self):
        state = initial()
        state['parameters']['grasp_offset'] = [0.,0.,-.03]
        step = dict(state=state, strategy='original')
        original = deepcopy(step)
        value, strategy = apply(step, dict(id=STRATEGY_ACTION, args=dict(value='observed_top')))
        self.assertEqual(original, step)
        self.assertEqual([0.,0.,0.], value['parameters']['grasp_offset'])
        self.assertEqual('observed_top', strategy)
        slow, strategy = apply(dict(state=value,strategy=strategy), dict(id='SET_TIME_SCALE',args=dict(value=3.)))
        self.assertEqual(3., slow['parameters']['time_scale'])
        self.assertEqual('observed_top', strategy)
