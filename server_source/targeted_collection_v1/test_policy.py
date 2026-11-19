"""预算与多解监督边界，避免把中间失败或未试动作变成成功标签。"""
import unittest
from policy import alternatives, outcome_set


def candidate(identifier, kind, profile='original'):
    return dict(id=identifier, kind=kind, state=dict(profile=profile))


class PolicyTests(unittest.TestCase):
    def test_routes_distinct_and_limit(self):
        rows = [candidate('a', 'descent_route', 'descent_minus45'),
                candidate('b', 'descent_route', 'descent_minus90'),
                candidate('c', 'exploratory_depth'), candidate('d', 'exploratory_slow')]
        got = alternatives(rows, rows[0])
        self.assertEqual(2, len(got))
        self.assertIn('b', [r['id'] for r in got])
        self.assertNotIn('a', [r['id'] for r in got])

    def test_same_kind_not_duplicated(self):
        rows = [candidate('a', 'measured_grasp'), candidate('b', 'exploratory_depth'),
                candidate('c', 'exploratory_depth'), candidate('d', 'exploratory_slow')]
        self.assertEqual(['b', 'd'], [r['id'] for r in alternatives(rows, rows[0])])

    def test_two_successes_remain_set(self):
        observed = [dict(action_id='a', terminal_success=True),
                    dict(action_id='b', terminal_success=True),
                    dict(action_id='c', terminal_success=False)]
        self.assertEqual(['a', 'b'], outcome_set(observed))

    def test_stage_progress_is_not_success(self):
        self.assertEqual([], outcome_set([dict(action_id='a', terminal_success=False)]))

    def test_unobserved_never_inferred(self):
        self.assertEqual(['a'], outcome_set([dict(action_id='a', terminal_success=True)]))


if __name__ == '__main__':
    unittest.main()
