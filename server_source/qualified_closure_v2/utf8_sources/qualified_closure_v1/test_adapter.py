import unittest
from qualified_closure_v1.adapter import guarded_close


class AdapterTests(unittest.TestCase):
    def test_rejected_check_never_calls_closure(self):
        calls = []
        def reject(result):
            raise ValueError('rejected')
        close = guarded_close(lambda flow: calls.append('closed'),
                              check=lambda flow: dict(passed=False), reject=reject)
        with self.assertRaisesRegex(ValueError, 'rejected'):
            close(None)
        self.assertEqual([], calls)

    def test_clear_check_preserves_original_arguments_and_return(self):
        calls = []
        def original(flow, *, loops):
            calls.append((flow, loops))
            return 'done'
        close = guarded_close(original, check=lambda flow: dict(passed=True), reject=lambda result: None)
        self.assertEqual('done', close('flow', loops=17))
        self.assertEqual([('flow', 17)], calls)

    def test_malformed_or_broken_rejection_handler_fails_closed(self):
        calls = []
        close = guarded_close(lambda flow: calls.append('closed'),
                              check=lambda flow: {}, reject=lambda result: None)
        with self.assertRaises(RuntimeError):
            close(None)
        self.assertEqual([], calls)


if __name__ == '__main__':
    unittest.main()
