"""验证非法输出隔离、无兜底与按同输入生成候选。"""
import json
import unittest
from copy import deepcopy
from unittest.mock import patch
from rc_common import SOURCE,read
from rc_policy import decide,parse,messages,visible_history


class PolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows=read(SOURCE/'verification.json')['rows']
        cls.step=next(r['step'] for r in rows if not r['success'])

    def test_retry_keeps_all_parameters(self):
        row=decide([self.step],[],method='retry')
        self.assertEqual(self.step['state'],row['selected']['state'])
        self.assertNotIn('event',row)

    def test_model_selects_shown_candidate(self):
        rule=decide([self.step],[],method='rule')
        selected=rule['candidates'][-1]
        with patch('rc_policy.generate',return_value={'text':json.dumps({'action_id':selected['id']})}):
            model=decide([self.step],[],method='model')
        self.assertEqual(rule['candidates'],model['candidates'])
        self.assertEqual(selected,model['selected'])

    def test_unknown_action_not_repaired(self):
        with patch('rc_policy.generate',return_value={'text':'{"action_id":"invented"}'}):
            row=decide([self.step],[],method='model')
        self.assertIsNone(row['selected'])
        self.assertIn('invalid',row)

    def test_service_failure_not_rule_fallback(self):
        with patch('rc_policy.generate',return_value={'service_failure':'timeout'}):
            row=decide([self.step],[],method='model')
        self.assertIsNone(row['selected'])
        self.assertEqual('timeout',row['service_failure'])

    def test_extra_output_fields_rejected(self):
        with self.assertRaises(ValueError):
            parse('{"action_id":"x","changes":{}}',[{'id':'x'}])

    def test_duplicate_keys_rejected(self):
        with self.assertRaises(ValueError):
            parse('{"action_id":"x","action_id":"x"}',[{'id':'x'}])

    def test_no_source_path_or_seed_in_prompt(self):
        rows=decide([self.step],[],method='rule')['candidates']
        text=json.dumps(messages(self.step,rows,[]))
        for private in ('result_path','result_sha256','initial_qpos','950401','/home/'):
            self.assertNotIn(private,text)

    def test_history_only_after_executed_action(self):
        decision=decide([self.step],[],method='rule')
        self.assertEqual([],visible_history([self.step],[decision]))
        second=deepcopy(self.step)
        second.update(index=2,success=True,feedback=None)
        history=visible_history([self.step,second],[decision])
        self.assertEqual(1,len(history))
        self.assertIsNone(history[0]['feedback'])

    def test_generation_does_not_mutate_source(self):
        original=deepcopy(self.step)
        decide([self.step],[],method='rule')
        self.assertEqual(original,self.step)


if __name__=='__main__':
    unittest.main()
