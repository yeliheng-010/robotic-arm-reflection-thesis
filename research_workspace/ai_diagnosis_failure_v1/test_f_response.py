import unittest
from boundary import build_request
from test_boundary import fixture
from f_response import finish, validate, MAX_TOKENS


class ResponseTests(unittest.TestCase):
    def test_actual_eos_required(self):
        self.assertEqual('stop', finish([1, 7], [7, 8]))
        self.assertEqual('length', finish([1]*MAX_TOKENS, [7]))
        with self.assertRaises(ValueError):
            finish([1, 2], [7])

    def test_truncated_valid_json_is_still_rejected(self):
        ledger, record = fixture()
        request = build_request(ledger, record)
        response = dict(finish_reason='length', text='{"action":{"id":"STOP","args":{}}}')
        self.assertFalse(validate(response, request, mode='direct')['valid'])

    def test_illegal_action_is_not_replaced(self):
        ledger, record = fixture()
        request = build_request(ledger, record)
        response = dict(finish_reason='stop', text='{"action":{"id":"RETRY","args":{}}}')
        checked = validate(response, request, mode='direct')
        self.assertFalse(checked['valid'])
        self.assertIsNone(checked['parsed'])


if __name__ == '__main__':
    unittest.main()
