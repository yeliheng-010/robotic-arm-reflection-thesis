"""主动观测决策接口的预算、隐私、历史与非法输出门禁。"""
import copy
import json
import unittest
from unittest.mock import patch
from ap_policy import observe
from loopstudy.actions import initial
from am_policy import context, messages, parse, history_entry, rule_action


def fixture():
    step=dict(index=1,state=initial(),result_sha256='x'*64,success=False,
        feedback=dict(error_type='empty_grasp',evidence={'grasp_residual_xy':[.03,.02],
        'motion_context':{'phase':'grasp_pose'}}))
    item=dict(seed=940301,source='RedBlock',factor_index=0)
    samples=observe(step,item,method='adaptive',used=2)['samples']
    return step,samples


class PolicyTests(unittest.TestCase):
    def test_budget_exhausted_rejects_observe(self):
        step,samples=fixture()
        value=context(step,samples,used=2)
        with self.assertRaises(ValueError):
            parse('{"action_id":"OBSERVE"}',value)

    def test_observe_legal_with_budget(self):
        step,samples=fixture()
        self.assertEqual('OBSERVE',parse('{"action_id":"OBSERVE"}',context(step,samples,used=0)))

    def test_duplicate_keys_and_extra_fields_rejected(self):
        step,samples=fixture()
        for text in ('{"action_id":"OBSERVE","action_id":"OBSERVE"}',
                     '{"action_id":"OBSERVE","reason":"x"}', '```json\n{}\n```'):
            with self.assertRaises(ValueError):
                parse(text,context(step,samples,used=0))

    def test_hidden_truth_cannot_reach_prompt(self):
        step,samples=fixture()
        value=context(step,samples,used=0)
        poisoned=copy.deepcopy(samples)
        poisoned[0]['audit']={'original':[999,999],'secret':'FORBIDDEN'}
        self.assertEqual(value,context(step,poisoned,used=0))
        text=json.dumps(messages(value,method='base_current',history=[]))
        for key in ('source_sha256','seed_components','FORBIDDEN','"audit"'):
            self.assertNotIn(key,text)

    def test_history_is_only_prompt_difference(self):
        step,samples=fixture()
        value=context(step,samples,used=0)
        history=[{'attempt':0,'action':{'id':'old'},'result':{'success':False}}]
        a=messages(value,method='base_current',history=history)
        b=messages(value,method='base_history',history=history)
        self.assertEqual(a[0],b[0])
        aa,bb=json.loads(a[1]['content']),json.loads(b[1]['content'])
        self.assertEqual([],aa.pop('history'))
        self.assertEqual(history,bb.pop('history'))
        self.assertEqual(aa,bb)

    def test_history_only_actions_and_visible_outcomes(self):
        step,samples=fixture()
        value=context(step,samples,used=0)
        selected=dict(id='a',state=step['state'],facts={'measurement':[99,99]},explanation='old residual')
        record=history_entry(value,selected,step)
        text=json.dumps(record)
        self.assertNotIn('residual_xy',text)
        self.assertNotIn('sha256',text)
        self.assertNotIn('audit',text)
        self.assertNotIn('measurement',text)
        self.assertNotIn('explanation',text)

    def test_rule_fixed_only_first_failure(self):
        step,samples=fixture()
        value=context(step,samples,used=0)
        self.assertEqual('OBSERVE',rule_action(value,method='fixed_first'))
        later=copy.deepcopy(step)
        later['index']=2
        value=context(later,samples,used=1)
        self.assertNotEqual('OBSERVE',rule_action(value,method='fixed_first'))

    def test_cross_state_rejected(self):
        step,samples=fixture()
        bad=copy.deepcopy(samples[0])
        bad['state']['profile']='changed'
        with self.assertRaises(AssertionError):
            context(step,samples+[bad],used=1)

    def test_success_has_no_failure_feedback(self):
        step,samples=fixture()
        value=context(step,samples,used=0)
        success=dict(step,index=2,success=True,feedback=None)
        record=history_entry(value,dict(id='a',state=step['state']),success)
        self.assertEqual(dict(attempt=2,success=True,error_type='none',phase=None),record['result'])

    def test_missing_failure_feedback_is_rejected(self):
        step,samples=fixture()
        value=context(step,samples,used=0)
        with self.assertRaises(AssertionError):
            history_entry(value,dict(id='a',state=step['state']),dict(step,feedback=None))


if __name__=='__main__':
    unittest.main()
