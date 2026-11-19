"""固定点差分和一阶条件诊断；不调用优化器。"""
import numpy as np
from scipy.optimize._numdiff import approx_derivative

ANGLE_SCALE = 1e-3
CONSTRAINT_SCALE = 1e-3
ORIGINAL_FTOL = 1e-14
COMPLEX_STEP = 1e-20
CROSS_STEP = 1e-24
CHECK_STEP = 1e-6


def complex_jacobian(fun, point, *, step):
    columns = []
    for index in range(len(point)):
        shifted = np.asarray(point, dtype=complex)
        shifted[index] += 1j * step
        columns.append(np.imag(fun(shifted)) / step)
    return np.column_stack(columns)


def directional_check(jacobian, gradient):
    _, singular, vectors = np.linalg.svd(jacobian)
    tangent = vectors[-1]
    if tangent[0] > 0:
        tangent = -tangent
    active_normal = np.array([1.0, 0.0, 0.0])
    matrix = np.column_stack([jacobian.T, active_normal])
    multipliers = np.linalg.solve(matrix, -gradient)
    return dict(singular_values=singular.tolist(), condition_number=float(singular[0]/singular[-1]),
        active_upper_normal=active_normal.tolist(), equality_multipliers=multipliers[:2].tolist(),
        upper_multiplier=float(multipliers[2]), inward_tangent=tangent.tolist(),
        inward_directional_derivative=float(gradient @ tangent),
        fitted_stationarity_inf=float(np.max(np.abs(gradient + matrix @ multipliers))),
        limitation='multipliers fitted at fixed point; not original solver internals or optimality proof')


def diagnose(fun, solved):
    point = np.asarray(solved['angles'])
    bounds = (np.asarray(solved['lower']), np.asarray(solved['upper']))
    jacobian = complex_jacobian(fun, point, step=COMPLEX_STEP)
    cross = complex_jacobian(fun, point, step=CROSS_STEP)
    default_step = float(np.sqrt(np.finfo(float).eps))
    forward = approx_derivative(fun, point, method='2-point', abs_step=default_step, bounds=bounds)
    central = approx_derivative(fun, point, method='3-point', abs_step=CHECK_STEP, bounds=bounds)
    np.testing.assert_allclose(jacobian, cross, atol=1e-10, rtol=1e-10)
    np.testing.assert_allclose(jacobian, central, atol=1e-6, rtol=1e-6)
    gradient = np.asarray(solved['delta']) / ANGLE_SCALE**2
    constraint = np.asarray(fun(point))
    return dict(complex_jacobian=jacobian.tolist(), default_fd_jacobian=forward.tolist(),
        default_fd_max_abs_error=float(np.max(np.abs(forward-jacobian))),
        three_point_max_abs_error=float(np.max(np.abs(central-jacobian))),
        complex_cross_max_abs_error=float(np.max(np.abs(cross-jacobian))),
        default_eps_rad=default_step, original_gradient=gradient.tolist(),
        reparameterized_gradient=(gradient*ANGLE_SCALE).tolist(),
        original_objective_hessian_diagonal=1/ANGLE_SCALE**2,
        reparameterized_objective_hessian_diagonal=1.0,
        scaled_constraint=constraint.tolist(),
        scaled_constraint_l1=float(np.sum(np.abs(constraint))), original_ftol=ORIGINAL_FTOL,
        original_ftol_constraint_length_scale_m=ORIGINAL_FTOL*CONSTRAINT_SCALE,
        upper_distance_rad=float(bounds[1][0]-point[0]),
        first_order=directional_check(jacobian, gradient))


def self_checks():
    linear = lambda x: np.array([x[0]+2*x[1], 3*x[2]])
    point = np.array([0.0, 0.002, -0.003])
    expected = np.array([[1.0, 2.0, 0.0], [0.0, 0.0, 3.0]])
    np.testing.assert_allclose(expected, complex_jacobian(linear, point, step=COMPLEX_STEP))
    checked_points = []
    def bounded(x):
        assert x[0] <= 0
        checked_points.append(x.tolist())
        return linear(x)
    actual = approx_derivative(bounded, point, method='2-point',
        abs_step=np.sqrt(np.finfo(float).eps), bounds=([-1, -1, -1], [0, 1, 1]))
    np.testing.assert_allclose(expected, actual, atol=1e-9, rtol=0)
    analytic = lambda x: np.array([np.sin(x[0]), np.cos(x[1])])
    expected = np.array([[np.cos(point[0]), 0, 0], [0, -np.sin(point[1]), 0]])
    np.testing.assert_allclose(expected, complex_jacobian(analytic, point, step=COMPLEX_STEP))
    return dict(passed=3, cases=['linear_complex_jacobian', 'bounded_difference', 'trigonometric_jacobian'])
