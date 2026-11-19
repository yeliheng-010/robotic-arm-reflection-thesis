import unittest
from unittest.mock import Mock, patch
from guard_runtime import guarded_open
from reflection.errors import TaskAbort


class ReleaseIntegrationTests(unittest.TestCase):
    def test_missing_hold_blocks_actual_open(self):
        self.check_rejected(dict(held=False, actual=[0., 0., 0.], expected=[0., 0., 0.]))

    def test_large_error_blocks_actual_open(self):
        self.check_rejected(dict(held=True, actual=[.2, 0., 0.], expected=[0., 0., 0.]))

    def check_rejected(self, evidence):
        original, trace = Mock(), {}
        with patch('guard_runtime.release_evidence', return_value=evidence):
            with self.assertRaises(TaskAbort):
                guarded_open(original, dict(source='RedBlock'), trace)(Mock())
        original.assert_not_called()
        self.assertFalse(trace['open_called'])

    def test_qualified_release_calls_original_once(self):
        original, trace, flow = Mock(), {}, Mock()
        evidence = dict(held=True, actual=[0., 0., 0.], expected=[0., 0., 0.])
        with patch('guard_runtime.release_evidence', return_value=evidence):
            guarded_open(original, dict(source='RedBlock'), trace)(flow, loops=1000)
        original.assert_called_once_with(flow, loops=1000)
        self.assertTrue(trace['open_called'])


if __name__ == '__main__':
    unittest.main()
