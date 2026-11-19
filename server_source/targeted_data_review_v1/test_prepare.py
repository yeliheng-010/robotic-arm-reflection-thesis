"""多成功、失败边界、延迟奖励和数据隔离测试。"""
import copy
import json
import unittest
from prepare import digest_input, pack, partition, sft_row


def fixture():
    choices = [dict(id=k, kind='example', state=dict(profile='original')) for k in ('a', 'b', 'c')]
    prompt = [dict(role='system', content='Choose'),
              dict(role='user', content=json.dumps(dict(candidates=choices)))]
    return dict(messages=prompt, input_hash=digest_input(prompt), scene_id='T0', seed=930001,
        after_attempt=1, candidate_count=3, successful_actions=['a', 'b'],
        tested_outcomes=[dict(action_id=k, terminal_success=True, immediate_success=False,
            following_attempts=2, kind='example', profile='original', trajectory_path='/'+k,
            trajectory_sha256='0'*64) for k in ('a', 'b')], split='train_candidate',
        source='expert_counterfactual_rule_continuation', model=None, training_approved=False,
        test_used=False, label_semantics='terminal_success_within_original_three_attempt_budget')


class PrepareTests(unittest.TestCase):
    def test_keep_both_and_unobserved_unknown(self):
        row = pack(fixture())
        self.assertEqual(['a', 'b'], row['accepted_action_ids'])
        self.assertEqual(['c'], row['untested_action_ids'])
        self.assertEqual([], row['observed_unsuccessful_action_ids'])
        self.assertEqual('delayed', row['success_timing'])

    def test_multi_cannot_be_flattened_into_single_sft(self):
        with self.assertRaises(ValueError):
            sft_row(pack(fixture()))

    def test_no_success_gets_no_assistant_target(self):
        raw = fixture()
        raw['successful_actions'] = []
        for o in raw['tested_outcomes']:
            o['terminal_success'] = False
        row = pack(raw)
        self.assertEqual([], row['accepted_action_ids'])
        self.assertEqual(['a', 'b'], row['observed_unsuccessful_action_ids'])
        with self.assertRaises(ValueError):
            sft_row(row)

    def test_reject_unlisted_action(self):
        raw = fixture()
        raw['tested_outcomes'][0]['action_id'] = 'forged'
        with self.assertRaises(ValueError):
            pack(raw)

    def test_reject_changed_input(self):
        raw = fixture()
        raw['messages'][0]['content'] = 'forged'
        with self.assertRaises(ValueError):
            pack(raw)

    def test_false_terminal_cannot_be_immediate_success(self):
        raw = fixture()
        raw['tested_outcomes'][0].update(terminal_success=False, immediate_success=True)
        with self.assertRaises(ValueError):
            pack(raw)

    def test_partition_quarantines_eval_overlap(self):
        raw = fixture()
        groups = partition([raw], held={raw['input_hash']}, old_train=set())
        self.assertEqual(0, len(groups['positive_sets']))
        self.assertEqual('evaluation_overlap', groups['quarantine'][0]['reason'])

    def test_duplicate_not_counted_twice(self):
        raw = fixture()
        with self.assertRaises(ValueError):
            partition([raw, copy.deepcopy(raw)], held=set(), old_train=set())

    def test_delayed_single_has_only_original_prompt_and_action(self):
        raw = fixture()
        raw['tested_outcomes'][1]['terminal_success'] = False
        raw['successful_actions'] = ['a']
        row = pack(raw)
        data = sft_row(row)
        self.assertEqual(raw['messages'], data['messages'][:-1])
        self.assertEqual({'action_id':'a'}, json.loads(data['messages'][-1]['content']))
        self.assertEqual('delayed', row['success_timing'])


if __name__ == '__main__':
    unittest.main()
