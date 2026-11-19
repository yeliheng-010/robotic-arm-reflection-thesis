"""硬步进门与证据捕获测试；禁止真实积分及场景初始化。"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from qualified_closure_dynamics_v1.limits import StepGate, guarded


class RuntimeTests(unittest.TestCase):
    def test_setup_cap_and_split_step_blocked(self):
        calls = []
        mj = SimpleNamespace(mj_step=lambda m, d: calls.append(1), mj_step1=None, mj_step2=None)
        with guarded(mj) as gate:
            gate.stage = 'setup'
            for _ in range(500):
                mj.mj_step(None, None)
            with self.assertRaises(ValueError):
                mj.mj_step(None, None)
            with self.assertRaises(RuntimeError):
                mj.mj_step1(None, None)
        self.assertEqual(500, len(calls))

    def test_task_requires_permit_and_bound_data(self):
        gate = StepGate(lambda m, d: None)
        model, data = object(), object()
        gate.stage = 'task'
        with self.assertRaises(ValueError):
            gate.call(model, data)
        gate.arm(model, data)
        with self.assertRaises(ValueError):
            gate.call(model, object())
        gate.call(model, data)
        with self.assertRaises(ValueError):
            gate.call(model, data)
        self.assertEqual(1, gate.task_steps)

    def test_extra_step_and_teardown_blocked(self):
        gate = StepGate(lambda m, d: None)
        gate.stage = 'task'
        gate.task_steps = 1000
        gate.arm(None, None)
        with self.assertRaises(ValueError):
            gate.call(None, None)
        gate.stage = 'blocked'
        with self.assertRaises(RuntimeError):
            gate.call(None, None)

    def test_capture_forwards_only_copy_and_keeps_timings_separate(self):
        from reflection.__main__ import bootstrap
        bootstrap()
        from qualified_closure_dynamics_v1 import capture
        live, private = object(), object()
        def packed(data):
            marker = 1.0 if data is live else 2.0
            return dict(qpos=np.asarray([marker]), warning_number=np.asarray([0]))
        with patch.object(capture, 'state', return_value=np.asarray([3.0])), \
             patch.object(capture, 'pack', side_effect=packed), \
             patch.object(capture, 'restore', return_value=private) as restore, \
             patch.object(capture, 'unpack', side_effect=lambda x: x), \
             patch.object(capture, 'collisions', side_effect=lambda m, d, s: d['qpos'].tolist()):
            row, arrays = capture.observe(None, live, source='source')
        self.assertEqual([1.0], row['cached_hits'])
        self.assertEqual([2.0], row['rebuilt_hits'])
        self.assertEqual(1, restore.call_count)
        self.assertEqual([1.0], arrays['cached_qpos'].tolist())

    def test_runtime_entry_missing_auth_never_imports_environment(self):
        from qualified_closure_dynamics_v1 import entry
        with patch.object(entry, 'authorization', side_effect=FileNotFoundError('authorization')):
            with self.assertRaises(FileNotFoundError):
                entry.main()


if __name__ == '__main__':
    unittest.main(verbosity=2)
