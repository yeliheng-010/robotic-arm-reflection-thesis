import unittest
from env_lease import retained
from live_budget import ObservationBudget


class FakeEnv:
    def __init__(self):
        self.closed = 0

    def close(self):
        self.closed += 1


class LeaseTests(unittest.TestCase):
    def test_inner_finally_close_is_deferred(self):
        env = FakeEnv()
        with retained(FakeEnv) as lease:
            try:
                pass
            finally:
                env.close()
            self.assertIs(env, lease.env)
            self.assertEqual(0, env.closed)
            env.close()
        self.assertEqual(1, env.closed)
        self.assertEqual(2, lease.close_requests)

    def test_exception_releases_and_restores_close(self):
        env, original = FakeEnv(), FakeEnv.close
        with self.assertRaisesRegex(RuntimeError, 'failure'):
            with retained(FakeEnv):
                env.close()
                raise RuntimeError('failure')
        self.assertEqual(1, env.closed)
        self.assertIs(original, FakeEnv.close)

    def test_extra_environment_not_leaked(self):
        a, b = FakeEnv(), FakeEnv()
        with self.assertRaises(RuntimeError):
            with retained(FakeEnv):
                a.close()
                b.close()
        self.assertEqual((1, 1), (a.closed, b.closed))

    def test_default_plus_two_observations_then_stop(self):
        budget = ObservationBudget(attempt=1, success=False)
        self.assertEqual([0, 1, 2], [budget.reserve() for _ in range(3)])
        self.assertEqual(0, budget.remaining)
        with self.assertRaises(ValueError):
            budget.reserve()

    def test_success_and_third_attempt_allow_default_only(self):
        for attempt, success in ((1, True), (3, False)):
            budget = ObservationBudget(attempt=attempt, success=success)
            self.assertEqual(0, budget.reserve())
            with self.assertRaises(ValueError):
                budget.reserve()


if __name__ == '__main__':
    unittest.main()
