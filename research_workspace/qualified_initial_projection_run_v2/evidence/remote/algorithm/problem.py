"""无量纲变量及复步长显式约束导数。"""
import numpy as np
from qualified_initial_projection_v1.solver import bounded_inputs

ANGLE_SCALE = 1e-3
CONSTRAINT_SCALE = 1e-3
COMPLEX_STEP = 1e-20
CONNECT_TOLERANCE = 1e-7
MAX_CHANGE = 0.01


class ScaledProblem:
    def __init__(self, reference, limits, *, residual):
        reference, low, high = bounded_inputs(reference, limits)
        self.reference, self.low, self.high = reference.copy(), low.copy(), high.copy()
        self.lower = (low-reference)/ANGLE_SCALE
        self.upper = (high-reference)/ANGLE_SCALE
        self.initial = (np.clip(reference, low, high)-reference)/ANGLE_SCALE
        self.residual = residual

    def angles(self, u):
        u = np.asarray(u)
        angles = self.reference + ANGLE_SCALE*u
        angles = np.where(u == self.lower, self.low, angles)
        return np.where(u == self.upper, self.high, angles)

    def objective(self, u):
        return 0.5*np.dot(u, u)

    def gradient(self, u):
        return np.asarray(u).copy()

    def full_residual(self, angles):
        value = np.asarray(self.residual(angles))
        if value.shape != (3,) or not np.isfinite(value).all():
            raise ValueError('Expected finite complete 3D residual')
        return value

    def constraint(self, u):
        return self.full_residual(self.angles(u))[1:]/CONSTRAINT_SCALE

    def jacobian(self, u):
        point = self.angles(u)
        columns = []
        for index in range(3):
            shifted = np.asarray(point, dtype=complex)
            shifted[index] += 1j*COMPLEX_STEP
            columns.append(self.full_residual(shifted).imag[1:]/COMPLEX_STEP)
        return np.column_stack(columns)*(ANGLE_SCALE/CONSTRAINT_SCALE)

    def acceptance(self, u, *, optimizer_success):
        u = np.asarray(u)
        if u.shape != (3,) or not np.isfinite(u).all():
            return dict(accepted=False, angles=None, delta=None, base_frame_residual=None)
        angles = self.angles(u)
        error = self.full_residual(angles)
        accepted = bool(optimizer_success and np.all(u >= self.lower) and np.all(u <= self.upper)
            and np.all(angles >= self.low) and np.all(angles <= self.high)
            and np.max(np.abs(angles-self.reference)) <= MAX_CHANGE
            and np.max(np.abs(error)) <= CONNECT_TOLERANCE)
        return dict(accepted=accepted, angles=angles.tolist(), delta=(angles-self.reference).tolist(),
                    base_frame_residual=error.tolist())
