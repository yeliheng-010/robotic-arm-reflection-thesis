"""约束投影器的定向回归，不创建仿真模型。"""
import unittest
import numpy as np
from qualified_initial_projection_v1.solver import solve_side


class SolverTests(unittest.TestCase):
    def reference(self):
        return np.array([0.000146, 0.003558, -0.00452])

    def limits(self):
        return np.array([[-1.57, 0.0], [-0.29670597283, 0.8], [-0.872664, 0.872664]])

    def test_linear_projection_matches_known_minimum(self):
        reference = self.reference()
        residual = lambda x: np.array([0.0, x[0] + x[1], x[2] + 0.002])
        result = solve_side(reference, self.limits(), residual=residual)
        expected = [(reference[0] - reference[1])/2, (reference[1] - reference[0])/2, -0.002]
        self.assertTrue(result['accepted'])
        np.testing.assert_allclose(expected, result['angles'], atol=1e-8, rtol=0)
        self.assertLessEqual(max(abs(x) for x in result['delta']), 0.01)

    def test_infeasible_constraint_is_rejected(self):
        residual = lambda x: np.array([0.0, x[0] - 1.0, x[2]])
        result = solve_side(self.reference(), self.limits(), residual=residual)
        self.assertFalse(result['accepted'])

    def test_nonfinite_reference_is_rejected_before_solver(self):
        reference = self.reference()
        reference[1] = np.nan
        with self.assertRaises(ValueError):
            solve_side(reference, self.limits(), residual=lambda x: np.zeros(3))

    def test_unselected_residual_component_cannot_pass(self):
        residual = lambda x: np.array([1e-3, x[0] + x[1], x[2] + 0.002])
        result = solve_side(self.reference(), self.limits(), residual=residual)
        self.assertFalse(result['accepted'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
