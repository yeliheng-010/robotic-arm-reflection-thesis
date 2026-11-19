"""只用资源替身验证禁止重复加载、live再次forward及损坏证据。"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from qualified_closure_mjb_v1.test_support import module


class ResourceTests(unittest.TestCase):
    def test_load_requires_explicit_permit_and_exact_path(self):
        code = module(self, 'resources')
        resources = code.Resources()
        resources.original_load = lambda path: object()
        path = str(code.PROJECT/code.proposal()['model']['path'])
        with self.assertRaises(ValueError):
            resources.load(path)
        resources.allow_load = True
        with self.assertRaises(ValueError):
            resources.load(path+'.wrong')
        resources.load(path)
        with self.assertRaises(ValueError):
            resources.load(path)

    def test_live_forward_once_and_copy_separate(self):
        resources = module(self, 'resources').Resources()
        model, live, private = object(), object(), object()
        resources.model = model
        resources.gate.bind(model, live)
        resources.original_forward = lambda m, d: None
        resources.forward(model, live)
        resources.forward(model, private)
        with self.assertRaises(ValueError):
            resources.forward(model, live)
        self.assertEqual((1, 1), (resources.counts['live_forward'], resources.counts['copy_forward']))

    def test_changed_binary_rejected_before_load(self):
        code = module(self, 'restore')
        with patch.object(code, 'sha', return_value='changed'), patch.object(code.mujoco.MjModel, 'from_binary_path') as load:
            with self.assertRaises(ValueError):
                code.load_model(SimpleNamespace(allow_load=False))
        load.assert_not_called()

    def test_missing_or_changed_model_field_rejected(self):
        code = module(self, 'restore')
        for changed in ({}, dict(signature='unexpected')):
            with patch.object(code, 'fields', return_value=changed), self.assertRaises(ValueError):
                code.model_identity(object())

    def test_rebuilt_array_mismatch_rejected(self):
        code = module(self, 'audit_states')
        values = dict(integration=np.array([7.]), cached_qpos=np.array([1.]), rebuilt_qpos=np.array([2.]))
        row = dict(cached_hits=[], rebuilt_hits=[])
        with patch.object(code, 'collisions', return_value=[]), patch.object(code, 'unpack', side_effect=lambda x: x), \
             patch.object(code, 'restore', return_value=object()), patch.object(code, 'state', return_value=values['integration']), \
             patch.object(code, 'pack', return_value=dict(qpos=np.array([3.]))):
            with self.assertRaises(AssertionError):
                code.check_state(None, values, row=row, metadata=dict(source='test'))

    def test_clock_mismatch_stops_without_another_step(self):
        code = module(self, 'worker')
        from qualified_closure_mjb_v1.test_support import Backend, Sink
        class ClockBad(Backend):
            def observe(self):
                if self.count:
                    raise ValueError('Simulation clock mismatch')
                return super().observe()
        backend = ClockBad()
        result = code.run_loop(backend, Sink(), clock=lambda: 0)
        self.assertEqual((1, 1, 0), (backend.count, result['completed_steps'], result['observed_steps']))
