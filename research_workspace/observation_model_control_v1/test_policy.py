"""真实候选输入边界与模型非法响应回归。"""
import copy
import json
import unittest
from unittest.mock import patch
from loopstudy.actions import initial
from om_policy import observe,inputs,prompt,decide


def fixture():
    step=dict(index=1,state=initial(),result_sha256='a'*64,feedback=dict(error_type='empty_grasp',
        evidence=dict(grasp_residual_xy=[.03,.02],motion_context={'phase':'grasp_pose'})))
    return step,dict(seed=940101,source='RedBlock',mechanism='outlier')


class PolicyTests(unittest.TestCase):
    def test_same_aggregation_same_inputs(self):
        step,item=fixture()
        for aggregation in ('latest','median'):
            a=observe(step,item,method='rule_'+aggregation,used=0)
            b=observe(step,item,method='base_'+aggregation,used=0)
            self.assertEqual(a,b)
            self.assertEqual(inputs(step,a),inputs(step,b))

    def test_prompt_has_no_audit_window_or_history(self):
        step,item=fixture()
        o=observe(step,item,method='base_median',used=0)
        messages=prompt(inputs(step,o))
        payload=json.loads(messages[1]['content'])
        self.assertEqual({'error','state','candidates','history','executor_profiles'},set(payload))
        # executor_profiles.original是公开执行配置名，不是传感器审计真值。
        text=json.dumps({k:v for k,v in payload.items() if k!='executor_profiles'})
        for forbidden in ('"original":','"audit":','"outlier":','"samples":','"selected":'):
            self.assertNotIn(forbidden,text.replace('\\"','"'))
        self.assertEqual([],payload['history'])
        changed=copy.deepcopy(o)
        changed['samples'][0]['audit']={'hidden_truth':'forged'}
        self.assertEqual(messages,prompt(inputs(step,changed)))

    def test_rule_never_calls_model(self):
        step,item=fixture()
        o=observe(step,item,method='rule_latest',used=0)
        with patch('om_policy.generate',side_effect=AssertionError('Unexpected model')):
            self.assertIsNone(decide(step,o,method='rule_latest')['model'])

    def test_invalid_choice_is_not_rule_fallback_or_retried(self):
        step,item=fixture()
        o=observe(step,item,method='base_latest',used=0)
        text='{"action_id":"unknown"}'
        event={'response':{},'text':text}
        with patch('om_policy.generate',return_value=event) as generate,patch('om_policy.check_response',return_value=text):
            result=decide(step,o,method='base_latest')
        self.assertEqual(1,generate.call_count)
        self.assertEqual('base',generate.call_args.args[0])
        self.assertIsNone(result['selected'])
        self.assertIn('invalid',result)

    def test_transport_failure_is_explicit(self):
        step,item=fixture()
        o=observe(step,item,method='base_latest',used=0)
        with patch('om_policy.generate',return_value={'error':'connection failed'}):
            self.assertTrue(decide(step,o,method='base_latest')['service_failure'])

    def test_future_state_uses_default_only(self):
        step,item=fixture()
        o=observe(step,item,method='base_median',used=2)
        self.assertEqual(1,len(o['samples']))
        self.assertEqual(0,o['extra_cost'])


if __name__=='__main__':
    unittest.main()
