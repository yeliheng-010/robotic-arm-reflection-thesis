"""避免把中间失败、隐藏真值或错误的绝对值计算当成合格样本。"""
import copy
import unittest
from screening import residual_check, visible_state, candidate_indices, sample_key


class ScreeningTests(unittest.TestCase):
    def test_delta_uses_current_absolute_offset(self):
        value = residual_check([-.05, 0], [-.25, 0, 0], [-.20, 0, 0])
        self.assertLess(value['dot'], 0)
        self.assertAlmostEqual(value['proxy_after_norm'], 0.)

    def test_missing_and_measured_zero_are_distinct(self):
        self.assertEqual('missing', residual_check(None, [0, 0, 0], [.02, 0, 0])['measurement'])
        self.assertEqual('present', residual_check([0, 0], [0, 0, 0], [.02, 0, 0])['measurement'])

    def test_only_immediately_successful_transition_is_candidate(self):
        records = [dict(accepted=False, reflection={'changes': {'time_scale': 1.5}}),
                   dict(accepted=False, reflection={'changes': {'time_scale': 2.}}),
                   dict(accepted=True, physical_success=True)]
        self.assertEqual([1], candidate_indices(records))
        records[2]['physical_success'] = False
        self.assertEqual([], candidate_indices(records))

    def test_noop_is_not_candidate(self):
        records = [dict(accepted=False, reflection={'changes': {}}),
                   dict(accepted=True, physical_success=True)]
        self.assertEqual([], candidate_indices(records))

    def test_visible_input_never_reads_hidden_error(self):
        run = dict(instruction='task', records=[{'parameters': {'time_scale': 1.},
                                                'error': {'hidden_truth': 'SECRET'}}],
                   feedback=[{'projected': {'error_type': 'empty_grasp', 'evidence': {}}, 'history': []}])
        state = visible_state(run, 0)
        self.assertNotIn('SECRET', str(state))
        self.assertEqual({}, state['error']['evidence'])

    def test_dedup_ignores_prose_but_keeps_supervision_source(self):
        state = {'history': [{'error': {'x': 1}, 'reflection': {'cause': 'first', 'changes': {'x': 2}}}]}
        other = copy.deepcopy(state)
        other['history'][0]['reflection']['cause'] = 'different prose'
        changes = {'place_offset': [.02, 0, 0]}
        self.assertEqual(sample_key(state, changes, source='llm'), sample_key(other, changes, source='llm'))
        self.assertNotEqual(sample_key(state, changes, source='llm'), sample_key(state, changes, source='rule_expert'))


if __name__ == '__main__':
    unittest.main()

