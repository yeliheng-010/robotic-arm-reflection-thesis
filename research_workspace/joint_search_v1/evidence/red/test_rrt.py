"""不依赖仿真器，验证绕障、方向、预算和失败关闭。"""
import math
import unittest
from js_rrt import search


def blocked(start, goal):
    for index in range(101):
        x, y = [a+(b-a)*index/100 for a,b in zip(start,goal)]
        if .4 <= x <= .6 and -.3 <= y <= .3:
            return False
    return True


class SearchTests(unittest.TestCase):
    def solve(self, check=blocked, **kwargs):
        options = dict(bounds=[(-1.,2.),(-1.,1.)], check=check, seed=42,
                       step=.2, max_checks=2000, max_nodes=1000, seconds=10.)
        options.update(kwargs)
        return search([0.,0.], [1.,0.], **options)

    def test_detours_around_obstacle(self):
        result = self.solve()
        self.assertEqual('found', result['status'])
        self.assertEqual([0.,0.], result['path'][0])
        self.assertEqual([1.,0.], result['path'][-1])
        self.assertTrue(all(blocked(a,b) for a,b in zip(result['path'],result['path'][1:])))
        self.assertEqual(result['path'], self.solve()['path'])

    def test_reverse_tree_checks_execution_direction(self):
        seen = []
        def directed(a,b):
            seen.append((tuple(a),tuple(b)))
            return b[0] >= a[0] and blocked(a,b)
        result = self.solve(directed)
        self.assertEqual('found', result['status'])
        self.assertTrue(all((tuple(a),tuple(b)) in seen
                            for a,b in zip(result['path'],result['path'][1:])))

    def test_edge_budget_is_hard_and_logged(self):
        events = []
        result = self.solve(lambda a,b: False, max_checks=7, on_check=events.append)
        self.assertEqual('check_budget', result['status'])
        self.assertIsNone(result['path'])
        self.assertEqual(7, result['checks'])
        self.assertEqual(7, len(events))

    def test_node_budget(self):
        result = self.solve(max_nodes=2)
        self.assertEqual('node_budget', result['status'])
        self.assertEqual(2, result['nodes'])

    def test_time_budget(self):
        ticks = iter(range(100))
        result = self.solve(clock=lambda: next(ticks), seconds=.5)
        self.assertEqual('time_budget', result['status'])
        self.assertEqual(0, result['checks'])

    def test_rejects_invalid_input(self):
        for kwargs in ({'step':0}, {'seconds':float('nan')}, {'max_checks':0},
                       {'bounds':[(0,.5),(-1,1)]}, {'bounds':[(0,math.inf),(-1,1)]}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.solve(**kwargs)

    def test_guard_exception_is_not_success(self):
        def broken(a,b):
            raise RuntimeError('guard unavailable')
        with self.assertRaises(RuntimeError):
            self.solve(broken)


if __name__ == '__main__':
    unittest.main(verbosity=2)
