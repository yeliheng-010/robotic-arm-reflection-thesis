import unittest
from unittest.mock import Mock
from qualified_task_v1.stop import once


class Done(BaseException):
    pass


class StopTests(unittest.TestCase):
    def test_finally_render_does_not_reobserve(self):
        observe, retain, env = Mock(), Mock(), object()
        render = once(observe, retain, complete=Done)
        for _ in range(2):
            with self.assertRaises(Done):
                render(env)
        observe.assert_called_once_with(env)
        retain.assert_called_once_with(env)

    def test_failure_reason_is_preserved(self):
        original = ValueError('qualification failed')
        observe, retain = Mock(side_effect=original), Mock()
        render = once(observe, retain, complete=Done)
        for _ in range(2):
            with self.assertRaises(ValueError) as caught:
                render(None)
            self.assertIs(original, caught.exception)
        self.assertEqual(1, observe.call_count)


if __name__ == '__main__':
    unittest.main()
