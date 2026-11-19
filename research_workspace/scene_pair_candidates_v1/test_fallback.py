"""候选可用时不变；补充候选仍受同一过滤器约束。"""
import unittest
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from grasp_process import GraspGroup
from candidate_runtime import filtering, EXHAUSTED


class FallbackTests(unittest.TestCase):
    def test_existing_candidates_return_without_generating(self):
        group = object()
        trace, arrays = {}, {}
        fn = filtering(lambda g, d: g, {}, trace, camera={}, arrays=arrays)
        self.assertIs(group, fn(group, None))
        self.assertEqual({}, trace)
        self.assertEqual({}, arrays)

    def test_unrelated_error_is_not_retried(self):
        def fail(group, detector):
            raise RuntimeError('unrelated')
        fn = filtering(fail, {}, {}, camera={}, arrays={})
        with self.assertRaisesRegex(RuntimeError, 'unrelated'):
            fn(None, None)

    def test_second_rejection_is_not_bypassed(self):
        from types import SimpleNamespace
        group = GraspGroup(np.zeros((1,17)))
        trace, arrays, calls = {}, {}, []
        def reject(candidate, detector):
            calls.append(candidate)
            raise RuntimeError(EXHAUSTED)
        fn = filtering(reject, {'points':np.zeros((64,3))}, trace, camera={}, arrays=arrays)
        with patch('candidate_runtime.generate', return_value=group):
            with self.assertRaisesRegex(RuntimeError, EXHAUSTED):
                fn(group, SimpleNamespace(scene_points=np.zeros((1,3))))
        self.assertEqual(2, len(calls))
        self.assertEqual(0, len(arrays['safe']))
