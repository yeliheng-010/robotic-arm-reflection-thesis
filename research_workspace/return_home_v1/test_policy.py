"""归位规则不允许增加关节范围或偷偷执行被拒绝路径。"""
import unittest
import math
from rh_policy import candidates, first_approved


class ReturnPolicyTests(unittest.TestCase):
    def test_direct_first_and_all_intermediate_combinations_are_unique(self):
        options = candidates([0.]*6, [1.]*6, duration=1.)
        self.assertEqual(63, len(options))
        self.assertEqual('direct', options[0]['id'])
        midpoints = [tuple(o['waypoints'][1]) for o in options[1:]]
        self.assertEqual(62, len(set(midpoints)))
        self.assertEqual([0., 0., 0., 0., 0., 1.], list(midpoints[0]))

    def test_endpoints_and_componentwise_bounds_are_preserved(self):
        start, goal = [-1., 2., -3., 4., -5., 6.], [1., -2., 3., -4., 5., -6.]
        options = candidates(start, goal, duration=1.)
        self.assertGreater(len(options), 0)
        for option in options:
            self.assertEqual(start, option['waypoints'][0])
            self.assertEqual(goal, option['waypoints'][-1])
            for point in option['waypoints']:
                self.assertTrue(all(min(a,b) <= x <= max(a,b) for x,a,b in zip(point,start,goal)))

    def test_duration_never_accelerates_a_leg_or_exceeds_double_budget(self):
        start, goal = [0.]*6, [1., 2., 3., 4., 5., 6.]
        options = candidates(start, goal, duration=2.)
        self.assertGreater(len(options), 0)
        for option in options:
            self.assertLessEqual(sum(option['durations']), 4.+1e-12)
            for a,b,t in zip(option['waypoints'], option['waypoints'][1:], option['durations']):
                self.assertGreater(t, 0.)
                self.assertLessEqual(max(abs(x-y) for x,y in zip(a,b))/t, 3.+1e-12)

    def test_degenerate_legs_are_not_proposed(self):
        options = candidates([0.]*6, [0., 0., 0., 0., 0., 1.], duration=1.)
        self.assertEqual(1, len(options))

    def test_invalid_inputs_are_rejected(self):
        for start, duration in [([0.]*5, 1.), ([math.nan]*6, 1.), ([0.]*6, 0.)]:
            with self.assertRaises(ValueError):
                candidates(start, [1.]*6, duration=duration)

    def test_first_safe_path_only(self):
        checked = []
        def probe(option):
            checked.append(option['id'])
            return dict(feasible=option['id'] == 'direct')
        selected, rows = first_approved(candidates([0.]*6, [1.]*6, duration=1.), probe)
        self.assertIsNotNone(selected)
        self.assertEqual('direct', selected['id'])
        self.assertEqual(['direct'], checked)
        self.assertEqual(1, len(rows))

    def test_all_rejected_has_no_fallback(self):
        selected, rows = first_approved(candidates([0.]*6, [1.]*6, duration=1.),
                                         lambda option: dict(feasible=False))
        self.assertIsNone(selected)
        self.assertEqual(63, len(rows))


if __name__ == '__main__':
    unittest.main()
