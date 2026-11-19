"""导出消息的错误目标与审计字段不得混入训练。"""
import json
import unittest
from curation import input_digest
from verify_output import validate_messages


def messages():
    value = dict(error={},state={},candidates=[dict(id='a')],history=[],executor_profiles={})
    return [dict(role='system',content='select'),
            dict(role='user',content=json.dumps(value)),
            dict(role='assistant',content='{"action_id":"a"}')]


class ExportTests(unittest.TestCase):
    def test_wrong_target_is_rejected(self):
        with self.assertRaises(AssertionError):
            validate_messages(messages(),'not-a-candidate')

    def test_hidden_audit_metadata_is_rejected(self):
        rows = messages()
        value = json.loads(rows[1]['content'])
        value['noise_audit'] = {'truth':1}
        rows[1]['content'] = json.dumps(value)
        with self.assertRaises(AssertionError):
            validate_messages(rows,'a')

    def test_json_key_order_is_not_new_sample(self):
        first = messages()[:-1]
        second = messages()[:-1]
        second[1]['content'] = json.dumps(json.loads(second[1]['content']),sort_keys=True)
        self.assertEqual(input_digest(first),input_digest(second))

    def test_numeric_change_stays_distinct(self):
        first = messages()[:-1]
        second = messages()[:-1]
        value = json.loads(second[1]['content'])
        value['state']['x'] = 0.00001
        second[1]['content'] = json.dumps(value)
        self.assertNotEqual(input_digest(first),input_digest(second))


if __name__=='__main__':
    unittest.main()
