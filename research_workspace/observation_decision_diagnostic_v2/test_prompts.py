"""菜单、理解探针、预算及源消息不可变的定向测试。"""
import copy
import json
import unittest
from od_prompts import variant,probe_expected,parse_probe,execution_prompt,eligible


def fixture():
    body=dict(candidates=[dict(id='a',kind='execute')],legal_action_ids=['OBSERVE','a'],
        quality={'grasp_residual_xy':{'status':'missing'}},remaining_observations=2,
        remaining_executions=1,history=[{'action':'old'}])
    return [dict(role='system',content='Original system'),dict(role='user',content=json.dumps(body))]


class PromptTests(unittest.TestCase):
    def test_baseline_exact_and_source_immutable(self):
        original=fixture()
        frozen=copy.deepcopy(original)
        self.assertEqual(original,variant(original,'baseline'))
        variant(original,'unified_first')
        variant(original,'missing_directive')
        self.assertEqual(frozen,original)

    def test_unified_only_adds_observation_candidate(self):
        source=fixture()
        result=variant(source,'unified_first')
        a,b=(json.loads(m[1]['content']) for m in (source,result))
        self.assertEqual(source[0],result[0])
        self.assertEqual('OBSERVE',b['candidates'].pop(0)['id'])
        self.assertEqual(a,b)

    def test_no_observe_entry_when_not_legal(self):
        source=fixture()
        body=json.loads(source[1]['content'])
        body['legal_action_ids']=['a']
        body['remaining_observations']=0
        source[1]['content']=json.dumps(body)
        result=json.loads(variant(source,'unified_first')[1]['content'])
        self.assertEqual(['a'],[r['id'] for r in result['candidates']])
        self.assertFalse(eligible(body))

    def test_probe_strict_schema_and_types(self):
        expected=probe_expected(json.loads(fixture()[1]['content']))
        self.assertEqual(expected,parse_probe(json.dumps(expected)))
        for bad in ('{"observe_legal":true,"observe_legal":false}',
                    '{"observe_legal":1,"observation_cost":1,"physical_cost":0,"remaining_observations":2}'):
            with self.assertRaises(ValueError):
                parse_probe(bad)

    def test_execution_phase_keeps_real_budget(self):
        body=json.loads(fixture()[1]['content'])
        messages=execution_prompt(body)
        value=json.loads(messages[1]['content'])
        self.assertEqual(2,value['remaining_observations'])
        self.assertEqual(['a'],value['legal_action_ids'])
        self.assertTrue(value['observation_phase_closed'])
        self.assertEqual([],value['history'])

    def test_eligibility_does_not_use_success(self):
        body=json.loads(fixture()[1]['content'])
        self.assertTrue(eligible(body))
        self.assertTrue(eligible(dict(body,future_success=False)))
        self.assertTrue(eligible(dict(body,future_success=True)))

    def test_last_position_preserves_physical_order(self):
        source=fixture()
        result=json.loads(variant(source,'unified_last')[1]['content'])
        self.assertEqual(['a','OBSERVE'],[r['id'] for r in result['candidates']])
        result['candidates'].pop()
        self.assertEqual(json.loads(source[1]['content']),result)


if __name__=='__main__':
    unittest.main()
