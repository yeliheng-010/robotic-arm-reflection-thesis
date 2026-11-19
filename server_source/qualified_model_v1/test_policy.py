import unittest
import json
from qualified_model_v1.policy import parse, pixel


class PolicyTests(unittest.TestCase):
    def test_accept(self):
        value = dict(action='LOCATE', source_pixel=[0, 1000], destination_pixel=[500, 500])
        self.assertEqual(value, parse(dict(text=json.dumps(value), finish_reason='stop')))
        self.assertEqual([0, 639], pixel(value['source_pixel'], width=640, height=640))

    def test_reject(self):
        for point in ([True, 20], [0, 1001], [1.5, 40], [100]):
            value = dict(action='LOCATE', source_pixel=point, destination_pixel=[1, 1])
            with self.assertRaises(ValueError):
                parse(dict(text=json.dumps(value), finish_reason='stop'))

    def test_stop_and_incomplete(self):
        self.assertEqual(dict(action='STOP'), parse(dict(text='{"action":"STOP"}', finish_reason='stop')))
        with self.assertRaises(ValueError):
            parse(dict(text='{"action":"STOP"}', finish_reason='length'))


if __name__ == '__main__':
    unittest.main()
