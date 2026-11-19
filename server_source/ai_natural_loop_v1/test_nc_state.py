import unittest
from nc_state import Branch


def step(index, *, success=False):
    return dict(index=index, success=success, state={'parameters': {}})


class BranchTests(unittest.TestCase):
    def test_observation_budget_is_shared_across_attempts(self):
        branch = Branch({}, step(1))
        branch.observe()
        branch.append(step(2))
        branch.observe()
        self.assertEqual(0, branch.remaining)
        with self.assertRaises(AssertionError):
            branch.observe()

    def test_three_attempts_no_fourth(self):
        branch = Branch({}, step(1))
        branch.append(step(2))
        branch.append(step(3))
        self.assertTrue(branch.terminal)
        with self.assertRaises(AssertionError):
            branch.append(step(4))

    def test_success_and_four_decision_cap(self):
        branch = Branch({}, step(1))
        for _ in range(4):
            branch.decide()
        with self.assertRaises(AssertionError):
            branch.decide()
        branch.append(step(2, success=True))
        with self.assertRaises(AssertionError):
            branch.observe()

    def test_shared_prefix_not_mutated_by_branch(self):
        first = step(1)
        a, b = Branch({}, first), Branch({}, first)
        a.ledger['steps'][0]['state']['parameters']['x'] = 1
        self.assertEqual({}, first['state']['parameters'])
        self.assertEqual({}, b.ledger['steps'][0]['state']['parameters'])


if __name__ == '__main__':
    unittest.main()
