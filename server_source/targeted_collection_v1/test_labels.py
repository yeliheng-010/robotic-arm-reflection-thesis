"""旧开发输入隔离与同输入矛盾不能被误报为单标签数据。"""
import unittest
from unittest.mock import patch
from labels import summarize


def row(key, success):
    return dict(input_hash=key, tested_outcomes=[dict(action_id='a', terminal_success=success)])


class LabelTests(unittest.TestCase):
    def test_eval_overlap_excluded_from_success_counts(self):
        values = [row('held', True), row('fresh', True)]
        with patch('labels.held_inputs', return_value=({'held'}, set())):
            counts = summarize(values)
        self.assertEqual(1, counts['eval_overlap'])
        self.assertEqual(1, counts['single_success'])
        self.assertTrue(values[0]['heldout_input_overlap'])

    def test_conflict_not_relabelled_as_success(self):
        with patch('labels.held_inputs', return_value=(set(), set())):
            counts = summarize([row('same', True), row('same', False)])
        self.assertEqual(1, counts['contradictory_observations'])
        self.assertEqual(0, counts['single_success'])
        self.assertEqual(0, counts['no_success'])


if __name__ == '__main__':
    unittest.main()
