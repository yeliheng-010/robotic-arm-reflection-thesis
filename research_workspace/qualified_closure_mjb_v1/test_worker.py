"""只用替身验证每步停止及证据中断，不请求真实积分。"""
import unittest
from qualified_closure_mjb_v1.test_support import module, Backend, Sink


class WorkerTests(unittest.TestCase):
    def test_either_timing_and_numeric_conditions_stop_at_k(self):
        worker = module(self, 'worker')
        for key in ('cached_hits', 'rebuilt_hits', 'nonfinite', 'warnings', 'model_changed'):
            backend = Backend(stop=key, at=2)
            sink = Sink()
            result = worker.run_loop(backend, sink, clock=lambda: 0)
            with self.subTest(key=key):
                self.assertEqual((2, 2, [0, 1, 2]), (backend.count, result['completed_steps'], sink.observations))
                self.assertEqual(2, len(sink.intents))

    def test_initial_rejection_zero_steps(self):
        worker = module(self, 'worker')
        backend = Backend(stop='cached_hits', at=0)
        self.assertEqual(0, worker.run_loop(backend, Sink(), clock=lambda: 0)['completed_steps'])

    def test_intent_failure_prevents_step(self):
        worker = module(self, 'worker')
        backend = Backend()
        result = worker.run_loop(backend, Sink(fail='intent'), clock=lambda: 0)
        self.assertEqual(0, backend.count)
        self.assertEqual(None, result['uncertain_step'])
        self.assertIn('engineering_failure', result['reasons'])

    def test_native_failure_preserves_uncertain_tail(self):
        result = module(self, 'worker').run_loop(Backend(error=True), Sink(), clock=lambda: 0)
        self.assertEqual((0, 1), (result['completed_steps'], result['uncertain_step']))

    def test_state_write_failure_keeps_returned_but_unobserved(self):
        backend = Backend()
        result = module(self, 'worker').run_loop(backend, Sink(fail='observed'), clock=lambda: 0)
        self.assertEqual((1, 1, 0), (backend.count, result['completed_steps'], result['observed_steps']))

    def test_timeout_before_first_step(self):
        times = iter([0, 121])
        result = module(self, 'worker').run_loop(Backend(), Sink(), clock=lambda: next(times))
        self.assertEqual((0, ['wall_timeout']), (result['completed_steps'], result['reasons']))

    def test_1000_controls_no_extra_step(self):
        backend, sink = Backend(), Sink()
        result = module(self, 'worker').run_loop(backend, sink, clock=lambda: 0)
        self.assertEqual((1000, ['budget_exhausted']), (backend.count, result['reasons']))
        self.assertEqual((1, 0.2), sink.intents[0])
        self.assertEqual((1000, 199.9999999999972), sink.intents[-1])
