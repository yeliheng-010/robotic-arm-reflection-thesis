"""先对旧接口复现缺少显式Jacobian，再对新接口检查相同契约。"""
import importlib
import importlib.util
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np


class ContractTests(unittest.TestCase):
    def test_optimizer_receives_explicit_constraint_jacobian(self):
        name = 'qualified_initial_projection_v2.solver'
        if importlib.util.find_spec(name) is None:
            name = 'qualified_initial_projection_v1.solver'
        target = importlib.import_module(name)
        owner = getattr(target, 'optimize', target)
        def fake(fun, initial, **kwargs):
            self.assertTrue(callable(kwargs['constraints'][0].get('jac')),
                            'Constraint Jacobian must be explicitly supplied')
            return SimpleNamespace(x=initial, success=False, status=8, message='test refusal', nit=1, nfev=1)
        with patch.object(owner, 'minimize', fake):
            target.solve_side(np.array([0.0, 0.002, -0.003]), np.array([[-1, 0], [-1, 1], [-1, 1]]),
                              residual=lambda x: np.array([0*x[0], x[1], x[2]]))


if __name__ == '__main__':
    unittest.main(verbosity=2)
