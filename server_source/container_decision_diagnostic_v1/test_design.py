"""关键防泄漏、合法动作与专家边界测试。"""
import json
import unittest
from copy import deepcopy
from cd_design import request, extra_actions
from cd_records import parse


class DesignTests(unittest.TestCase):
    def setUp(self):
        self.rows = [dict(id='one'), dict(id='two')]
        body = dict(candidates=self.rows, legal_action_ids=['one','two'], history=[])
        self.case = dict(request=dict(messages=[dict(role='system',content='s'),
            dict(role='user',content=json.dumps(body))]), snapshot=dict(
                state=dict(parameters=dict(lift_height=.35)), feedback=dict(
                    error_type='ik_failure',evidence=dict(motion_context=dict(phase='carry_transport')))))

    def test_exact_request(self):
        self.assertEqual(self.case['request'], request(self.case,'replay'))

    def test_reverse_both_orders(self):
        body = json.loads(request(self.case,'reverse')['messages'][1]['content'])
        self.assertEqual(['two','one'],body['legal_action_ids'])
        self.assertEqual(list(reversed(self.rows)),body['candidates'])

    def test_no_source_mutation(self):
        before = deepcopy(self.case)
        request(self.case,'reverse')
        extra_actions(self.case)
        self.assertEqual(before,self.case)

    def test_future_results_do_not_affect_prompts(self):
        original = request(self.case,'summary')
        self.case.update(rule_success=True,model_success=False,future_labels=['two'])
        self.assertEqual(original,request(self.case,'summary'))

    def test_expert_hint_separate(self):
        text = request(self.case,'expert_hint')['messages'][1]['content']
        self.assertIn('专家启发式干预',text)
        self.assertNotEqual(text,request(self.case,'summary')['messages'][1]['content'])

    def test_lift_only_at_transport_ik(self):
        self.assertEqual([.20,.25,.30],[r['state']['parameters']['lift_height'] for r in extra_actions(self.case)])
        self.case['snapshot']['feedback']['evidence']['motion_context']['phase']='grasp_pose'
        self.assertEqual([],extra_actions(self.case))

    def test_invalid_action_rejected(self):
        with self.assertRaises(ValueError):
            parse('{"action_id":"missing"}',self.rows)

    def test_duplicate_key_rejected(self):
        with self.assertRaises(ValueError):
            parse('{"action_id":"one","action_id":"two"}',self.rows)


if __name__ == '__main__':
    unittest.main()
