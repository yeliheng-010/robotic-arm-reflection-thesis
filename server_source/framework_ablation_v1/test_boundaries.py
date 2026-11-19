"""请求身份、无重试、非法输出及可见输入隔离边界。"""
import copy
import unittest
from unittest.mock import patch
import client
from audit_task import model_check
from loopstudy.selection import messages


class BoundaryTests(unittest.TestCase):
    def test_base_and_tuned_only_differ_by_model(self):
        prompt=[dict(role='system',content='choose'),dict(role='user',content='{}')]
        before=client.payload_for('base',prompt)
        after=client.payload_for('new189',prompt)
        self.assertNotEqual(before.pop('model'),after.pop('model'))
        self.assertEqual(before,after)
        self.assertEqual(prompt,before['messages'])

    def test_network_failure_not_retried(self):
        with patch.object(client,'request',side_effect=ConnectionError('offline')) as call:
            result=client.generate('base',[],max_tokens=128)
        self.assertEqual(1,call.call_count)
        self.assertTrue(result['service_error'])
        self.assertIn('error',result)

    def test_wrong_identity_and_truncation_rejected(self):
        response=dict(model=client.ALIASES['base'],identity={'frozen':1},
                      active_method='base',active_adapter_sha256=None,
                      choices=[dict(finish_reason='stop',message=dict(content='{}'))])
        with patch.object(client,'model_identity',return_value={'frozen':1}):
            with self.assertRaises(AssertionError):
                client.check_response(response,'new189')
            response['choices'][0]['finish_reason']='length'
            with self.assertRaises(ValueError):
                client.check_response(response,'base')

    def test_modified_model_input_rejected_before_physics(self):
        decision=dict(feedback={},before={},candidates=[dict(id='a',state={})])
        prompt=messages({}, {},rows=decision['candidates'],history=[])
        decision['event']=dict(request=client.payload_for('base',prompt))
        decision['event']['request']['messages'][1]['content']='{"truth":"hidden"}'
        with self.assertRaises(AssertionError):
            model_check(decision,[],method='current')

    def test_same_alias_wrong_active_adapter_rejected(self):
        response=dict(model=client.ALIASES['new189'],identity={'frozen':1},
                      active_method='previous159',active_adapter_sha256='old')
        with patch.object(client,'model_identity',return_value={'frozen':1}):
            with self.assertRaises(AssertionError):
                client.check_response(response,'new189')

    def test_same_method_wrong_adapter_hash_rejected(self):
        response=dict(model=client.ALIASES['new189'],identity={'frozen':1},
                      active_method='new189',active_adapter_sha256='old')
        with patch.object(client,'model_identity',return_value={'frozen':1}), \
             patch.object(client,'requested_adapter',return_value='new'):
            with self.assertRaises(AssertionError):
                client.check_response(response,'new189')


if __name__=='__main__':
    unittest.main()
