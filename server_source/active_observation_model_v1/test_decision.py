"""验证模型补看费用、非法响应终止及历史递交。"""
import unittest
from unittest.mock import patch
from am_decision import decide
from am_common import scenes,SHARDS,SMOKE_SEEDS
from test_policy import fixture


class DecisionTests(unittest.TestCase):
    def test_invalid_output_has_no_rule_fallback(self):
        step,_=fixture()
        item=dict(seed=940301,source='RedBlock',factor_index=0)
        with patch('am_decision.generate',return_value={'text':'bad'}):
            d=decide(step,item,method='base_current',used=0,history=[])
        self.assertIsNone(d['selected'])
        self.assertTrue(d['invalid'])
        self.assertEqual(0,d['observation']['extra_cost'])

    def test_repeated_observe_exhausts_budget_then_fails(self):
        step,_=fixture()
        item=dict(seed=940301,source='RedBlock',factor_index=0)
        with patch('am_decision.generate',return_value={'text':'{"action_id":"OBSERVE"}'}) as call:
            d=decide(step,item,method='base_history',used=0,history=[])
        self.assertEqual(3,call.call_count)
        self.assertEqual(2,d['observation']['extra_cost'])
        self.assertIsNone(d['selected'])
        self.assertTrue(d['invalid'])

    def test_transport_failure_is_not_format_failure(self):
        step,_=fixture()
        item=dict(seed=940301,source='RedBlock',factor_index=0)
        with patch('am_decision.generate',return_value={'service_failure':'timeout'}):
            d=decide(step,item,method='base_current',used=0,history=[])
        self.assertEqual('timeout',d['service_failure'])
        self.assertIsNone(d['invalid'])

    def test_new_design_and_shards(self):
        rows=scenes()
        self.assertEqual(24,len(rows))
        self.assertEqual(6,len({r['seed'] for r in rows}))
        smoke=[r for r in rows if r['seed'] in SMOKE_SEEDS]
        self.assertEqual([2,1,1],[len(smoke[s::SHARDS]) for s in range(SHARDS)])
        self.assertEqual([8,8,8],[len(rows[s::SHARDS]) for s in range(SHARDS)])


if __name__=='__main__':
    unittest.main()
