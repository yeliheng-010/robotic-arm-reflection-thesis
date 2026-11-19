"""批量门禁不得复用其他教师/代码版本的pilot通过标记。"""
import copy
import os
import unittest


def check(gate, configuration):
    if os.environ.get('CHECK_ORIGINAL_GATE'):
        assert gate['allow_batch']
        return
    from stability.audit import validate_gate
    validate_gate(gate, configuration)


class GateTests(unittest.TestCase):
    def test_rejects_stale_pilot_for_each_frozen_component(self):
        config = {'code': {'hash': 'a'}, 'collection_code': {'hash': 'b'}, 'teacher': {'model': '9B'}}
        for field in config:
            gate = dict(copy.deepcopy(config), allow_batch=True)
            gate[field] = {'changed': True}
            with self.subTest(field=field), self.assertRaises(AssertionError):
                check(gate, config)

    def test_matching_passed_pilot_is_accepted(self):
        config = {'code': {}, 'collection_code': {}, 'teacher': {}}
        check(dict(config, allow_batch=True), config)
        with self.assertRaises(AssertionError):
            check(dict(config, allow_batch=False), config)


if __name__ == '__main__':
    unittest.main()

