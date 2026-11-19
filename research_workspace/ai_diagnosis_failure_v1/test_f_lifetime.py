import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from f_lifetime import managed


class FakeEnv:
    def __init__(self, *, fail=False):
        self.calls, self.fail = 0, fail

    def close(self):
        self.calls += 1
        if self.fail:
            raise RuntimeError('close_failure')


class LifetimeTests(unittest.TestCase):
    def test_observation_exception_closes_once_and_records(self):
        original = FakeEnv.close
        with TemporaryDirectory() as temporary:
            folder = Path(temporary)
            with self.assertRaisesRegex(ValueError, 'post_observation'):
                with managed(FakeEnv, folder) as lease:
                    env = FakeEnv()
                    env.close()
                    lease.mark_retained()
                    self.assertEqual(0, env.calls)
                    raise ValueError('post_observation')
            row = json.loads((folder/'lifecycle.json').read_text())
            self.assertTrue(row['released'])
            self.assertEqual(1, env.calls)
            self.assertEqual('ValueError', row['exit_exception'])
        self.assertIs(original, FakeEnv.close)

    def test_close_failure_never_claims_release(self):
        with TemporaryDirectory() as temporary:
            folder = Path(temporary)
            with self.assertRaisesRegex(RuntimeError, 'close_failure'):
                with managed(FakeEnv, folder):
                    env = FakeEnv(fail=True)
                    env.close()
            row = json.loads((folder/'lifecycle.json').read_text())
            self.assertFalse(row['released'])
            self.assertEqual('RuntimeError', row['close_error'])
            self.assertEqual(1, env.calls)

    def test_no_environment_is_explicit(self):
        with TemporaryDirectory() as temporary:
            folder = Path(temporary)
            with managed(FakeEnv, folder):
                pass
            row = json.loads((folder/'lifecycle.json').read_text())
            self.assertFalse(row['environment_retained'])
            self.assertFalse(row['released'])


if __name__ == '__main__':
    unittest.main()
