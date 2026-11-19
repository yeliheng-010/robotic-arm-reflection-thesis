"""原生计数分别表示请求/返回；禁止setup、额外步和错误数据。"""
import unittest
from qualified_closure_mjb_v1.test_support import module


class LimitTests(unittest.TestCase):
    def gate(self, callback=lambda m, d: None):
        g = module(self, 'limits').StepGate(callback)
        m, d = object(), object()
        g.bind(m, d)
        return g, m, d

    def test_no_setup_or_unpermitted_step(self):
        gate, m, d = self.gate()
        for stage in ('blocked', 'setup', 'task'):
            gate.stage = stage
            with self.subTest(stage=stage), self.assertRaises(ValueError):
                gate.call(m, d)
        self.assertEqual((0, 0), (gate.requests, gate.returns))

    def test_single_permit_and_return(self):
        gate, m, d = self.gate()
        gate.stage = 'task'
        gate.arm(m, d)
        gate.call(m, d)
        self.assertEqual((1, 1, False), (gate.requests, gate.returns, gate.pending))
        with self.assertRaises(ValueError):
            gate.call(m, d)

    def test_wrong_model_data_and_frameskip(self):
        for kind in ('model', 'data', 'frame'):
            gate, m, d = self.gate()
            gate.stage = 'task'
            gate.arm(m, d)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                gate.call(object() if kind == 'model' else m, object() if kind == 'data' else d,
                          nstep=2 if kind == 'frame' else 1)
            self.assertEqual((0, 0), (gate.requests, gate.returns))

    def test_native_exception_is_request_without_return(self):
        def native(m, d):
            raise RuntimeError('partial native work possible')
        gate, m, d = self.gate(native)
        gate.stage = 'task'
        gate.arm(m, d)
        with self.assertRaises(RuntimeError):
            gate.call(m, d)
        self.assertEqual((1, 0, False), (gate.requests, gate.returns, gate.pending))

    def test_cap_and_rebinding(self):
        gate, m, d = self.gate()
        with self.assertRaises(ValueError):
            gate.bind(m, object())
        gate.stage = 'task'
        gate.requests = 1000
        with self.assertRaises(ValueError):
            gate.arm(m, d)

    def test_split_step_forbidden(self):
        with self.assertRaises(RuntimeError):
            module(self, 'limits').forbid(None, None)
