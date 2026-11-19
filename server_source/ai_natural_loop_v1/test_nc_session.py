from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
import nc_session


class FakeEnv:
    def __init__(self):
        self.closes = 0

    def close(self):
        self.closes += 1


def execute(session):
    session.folder.mkdir(parents=True)
    def defer(env):
        session.lease.defer(env)
    with patch.object(FakeEnv, 'close', defer):
        env = FakeEnv()
        env.close()
    session.lease.mark_retained()


class OwnershipTests(unittest.TestCase):
    def test_nested_branch_does_not_capture_or_close_shared_env(self):
        with TemporaryDirectory() as temporary, patch.object(nc_session, 'UR5GraspEnv', FakeEnv), \
             patch.object(nc_session.Session, 'execute', execute):
            root = Path(temporary)
            with nc_session.opened({}, {}, folder=root/'first', index=1) as first:
                with nc_session.opened({}, {}, folder=root/'second', index=2) as second:
                    self.assertIsNot(first.lease.env, second.lease.env)
                self.assertEqual(1, second.lease.env.closes)
                self.assertEqual(0, first.lease.env.closes)
            self.assertEqual(1, first.lease.env.closes)

    def test_inner_exception_closes_both_once_without_swallowing(self):
        with TemporaryDirectory() as temporary, patch.object(nc_session, 'UR5GraspEnv', FakeEnv), \
             patch.object(nc_session.Session, 'execute', execute):
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, 'probe'):
                with nc_session.opened({}, {}, folder=root/'first', index=1) as first:
                    with nc_session.opened({}, {}, folder=root/'second', index=2) as second:
                        raise ValueError('probe')
            self.assertEqual([1, 1], [first.lease.env.closes, second.lease.env.closes])


if __name__ == '__main__':
    unittest.main()
