"""四组身份及串行adapter切换的回归边界。"""
import importlib.util
import unittest
from contextlib import contextmanager
from common import METHODS, ALIASES


class FakeModel:
    def __init__(self):
        self.active_adapter = 'previous159'
        self.disabled = False

    def set_adapter(self, name):
        self.active_adapter = name

    def eval(self):
        return self

    @contextmanager
    def disable_adapter(self):
        self.disabled = True
        try:
            yield
        finally:
            self.disabled = False


class AdapterTests(unittest.TestCase):
    def route(self):
        self.assertIsNotNone(importlib.util.find_spec('adapter_route'))
        from adapter_route import activate
        return activate

    def test_four_explicit_methods(self):
        self.assertEqual(('retry', 'rule', 'current', 'history'), METHODS)
        self.assertEqual({'base', 'previous159', 'new189'}, set(ALIASES))
        self.assertEqual(3, len(set(ALIASES.values())))

    def test_alternating_models_and_restoration(self):
        model, activate = FakeModel(), self.route()
        for method in ('new189', 'base', 'previous159', 'base', 'new189'):
            with activate(model, method):
                self.assertEqual(method == 'base', model.disabled)
                if method != 'base':
                    self.assertEqual(method, model.active_adapter)
            self.assertEqual('previous159', model.active_adapter)
            self.assertFalse(model.disabled)

    def test_exception_restores_adapter(self):
        model, activate = FakeModel(), self.route()
        with self.assertRaisesRegex(RuntimeError, 'generation failed'):
            with activate(model, 'new189'):
                raise RuntimeError('generation failed')
        self.assertEqual('previous159', model.active_adapter)
        self.assertFalse(model.disabled)

    def test_unknown_model_rejected(self):
        model, activate = FakeModel(), self.route()
        with self.assertRaises(ValueError):
            with activate(model, 'unknown'):
                self.fail('Unknown model entered generation')


if __name__ == '__main__':
    unittest.main()
