"""重参数化、导数及严格拒绝的定向测试；无真实求解。"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from scipy.optimize._numdiff import approx_derivative
from qualified_initial_projection_v2.problem import ScaledProblem, ANGLE_SCALE
from qualified_initial_projection_v2 import solver


class ProblemTests(unittest.TestCase):
    def problem(self, residual=None):
        return ScaledProblem([0.0001464011158215543, 0.003558, -0.004520],
            [[-1.57, 0], [-0.2967, 0.8], [-0.872664, 0.872664]],
            residual=residual or (lambda x: np.array([0*x[0], x[0]+2*x[1], 3*x[2]])))

    def test_objective_and_gradient_equivalence(self):
        p = self.problem()
        u = np.array([-1.0, 0.4, -0.7])
        x = p.angles(u)
        self.assertAlmostEqual(0.5*np.sum(((x-p.reference)/ANGLE_SCALE)**2), p.objective(u))
        np.testing.assert_allclose((x-p.reference)/ANGLE_SCALE, p.gradient(u), atol=1e-14)

    def test_linear_constraint_chain_rule(self):
        p = self.problem()
        np.testing.assert_allclose([[1, 2, 0], [0, 0, 3]], p.jacobian(p.initial), atol=1e-14)

    def test_nonlinear_jacobian(self):
        p = self.problem(lambda x: np.array([0*x[0], np.sin(x[0])+x[1]**2, np.cos(x[2])]))
        u = np.array([-1.0, 0.4, -0.7])
        x = p.angles(u)
        expected = [[np.cos(x[0]), 2*x[1], 0], [0, 0, -np.sin(x[2])]]
        np.testing.assert_allclose(expected, p.jacobian(u), atol=1e-14)
        numeric = approx_derivative(p.constraint, u, method='3-point', abs_step=1e-3)
        np.testing.assert_allclose(expected, numeric, atol=1e-7, rtol=1e-7)

    def test_original_bounds_and_initial_are_preserved(self):
        p = self.problem()
        np.testing.assert_array_equal(p.low, p.angles(p.lower))
        np.testing.assert_array_equal(p.high, p.angles(p.upper))
        np.testing.assert_array_equal(np.clip(p.reference, p.low, p.high), p.angles(p.initial))
        self.assertEqual(0.0, p.angles(p.upper)[0])

    def test_success_zero_residual_can_pass(self):
        p = self.problem(lambda x: x*0)
        self.assertTrue(p.acceptance(p.initial, optimizer_success=True)['accepted'])

    def test_failed_optimizer_cannot_be_overridden(self):
        p = self.problem(lambda x: x*0)
        self.assertFalse(p.acceptance(p.initial, optimizer_success=False)['accepted'])

    def test_outside_u_is_rejected_without_clipping(self):
        p = self.problem(lambda x: x*0)
        u = p.initial.copy()
        u[0] = p.upper[0]+1e-6
        self.assertGreater(p.angles(u)[0], 0)
        self.assertFalse(p.acceptance(u, optimizer_success=True)['accepted'])

    def test_full_3d_residual_rejects_ignored_component(self):
        p = self.problem(lambda x: np.array([1e-6+0*x[0], 0*x[1], 0*x[2]]))
        self.assertFalse(p.acceptance(p.initial, optimizer_success=True)['accepted'])

    def test_nonfinite_inputs_and_outputs(self):
        with self.assertRaises(ValueError):
            ScaledProblem([np.nan, 0, 0], [[-1, 1]]*3, residual=lambda x: x)
        p = self.problem()
        self.assertFalse(p.acceptance([np.nan, 0, 0], optimizer_success=True)['accepted'])
        with self.assertRaises(ValueError):
            self.problem(lambda x: np.full(3, np.nan)).constraint(p.initial)

    def test_degenerate_bounds_rejected(self):
        with self.assertRaises(ValueError):
            ScaledProblem([0, 0, 0], [[0, 0], [-1, 1], [-1, 1]], residual=lambda x: x)

    def test_adapter_records_one_call_and_preserves_failure(self):
        p = self.problem()
        def fake(fun, initial, **kwargs):
            self.assertEqual(dict(maxiter=200, ftol=1e-14, disp=False), kwargs['options'])
            kwargs['callback'](initial)
            return SimpleNamespace(x=initial, success=False, status=8, message='test refusal', nit=1, nfev=1)
        with patch.object(solver.optimize, 'minimize', side_effect=fake) as mocked:
            result = solver.solve_side(p.reference, np.column_stack([p.low, p.high]), residual=lambda x: x*0)
        self.assertEqual(1, mocked.call_count)
        self.assertFalse(result['accepted'])
        self.assertEqual(1, len(result['major_iteration_trace']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
