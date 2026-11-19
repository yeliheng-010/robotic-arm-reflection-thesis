"""固定预算的局部几何投影；不积分、不多起点重试。"""
import numpy as np
from scipy.optimize import minimize

MAX_DELTA_RAD = 0.01
ANGLE_SCALE_RAD = 1e-3
CONSTRAINT_SCALE_M = 1e-3
CONNECT_TOLERANCE_M = 1e-7
MAX_ITERATIONS = 200
OPTIMIZER_FTOL = 1e-14


def bounded_inputs(reference, limits):
    reference, limits = np.asarray(reference, dtype=float), np.asarray(limits, dtype=float)
    if reference.shape != (3,) or limits.shape != (3, 2):
        raise ValueError('Expected three passive joints and ranges')
    if not np.isfinite(reference).all() or not np.isfinite(limits).all():
        raise ValueError('Nonfinite projection inputs')
    low = np.maximum(limits[:, 0], reference - MAX_DELTA_RAD)
    high = np.minimum(limits[:, 1], reference + MAX_DELTA_RAD)
    if np.any(low >= high):
        raise ValueError('Empty or degenerate projection bounds')
    return reference, low, high


def solve_side(reference, limits, *, residual):
    reference, low, high = bounded_inputs(reference, limits)
    initial = np.clip(reference, low, high)
    objective = lambda x: 0.5 * np.sum(((x - reference) / ANGLE_SCALE_RAD)**2)
    gradient = lambda x: (x - reference) / ANGLE_SCALE_RAD**2
    constraint = lambda x: np.asarray(residual(x))[1:] / CONSTRAINT_SCALE_M
    solved = minimize(objective, initial, method='SLSQP', jac=gradient,
        bounds=list(zip(low, high)), constraints=[dict(type='eq', fun=constraint)],
        options=dict(maxiter=MAX_ITERATIONS, ftol=OPTIMIZER_FTOL, disp=False))
    angles, error = np.asarray(solved.x), np.asarray(residual(solved.x))
    finite = bool(np.isfinite(angles).all() and np.isfinite(error).all())
    accepted = bool(solved.success and finite and error.shape == (3,)
                    and np.all(angles >= low) and np.all(angles <= high)
                    and np.max(np.abs(error)) <= CONNECT_TOLERANCE_M
                    and np.max(np.abs(angles - reference)) <= MAX_DELTA_RAD)
    return dict(accepted=accepted, optimizer_success=bool(solved.success), status=int(solved.status),
        message=str(solved.message), iterations=int(solved.nit), evaluations=int(solved.nfev),
        angles=angles.tolist() if finite else None, delta=(angles - reference).tolist() if finite else None,
        base_frame_residual=error.tolist() if finite else None,
        objective=float(objective(angles)) if finite else None, initial=initial.tolist(),
        lower=low.tolist(), upper=high.tolist(), attempts=1, global_minimum_proven=False)
