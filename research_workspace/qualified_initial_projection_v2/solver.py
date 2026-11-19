"""一次局部求解适配器；本轮仅以测试替身验证，不授权真实调用。"""
import numpy as np
from scipy import optimize
from qualified_initial_projection_v2.problem import ScaledProblem

MAX_ITERATIONS = 200
OPTIMIZER_FTOL = 1e-14


def solve_side(reference, limits, *, residual):
    problem = ScaledProblem(reference, limits, residual=residual)
    trace = []
    def record(u):
        trace.append(dict(u=np.asarray(u).tolist(), angles=problem.angles(u).tolist(),
                          objective=float(problem.objective(u)), constraint=problem.constraint(u).tolist()))
    solved = optimize.minimize(problem.objective, problem.initial, method='SLSQP',
        jac=problem.gradient, bounds=list(zip(problem.lower, problem.upper)),
        constraints=[dict(type='eq', fun=problem.constraint, jac=problem.jacobian)],
        callback=record, options=dict(maxiter=MAX_ITERATIONS, ftol=OPTIMIZER_FTOL, disp=False))
    result = problem.acceptance(solved.x, optimizer_success=bool(solved.success))
    result.update(optimizer_success=bool(solved.success), status=int(solved.status), message=str(solved.message),
        iterations=int(solved.nit), evaluations=int(solved.nfev), attempts=1,
        initial=problem.angles(problem.initial).tolist(), initial_u=problem.initial.tolist(),
        lower=problem.low.tolist(), upper=problem.high.tolist(),
        major_iteration_trace=trace, trace_includes_internal_line_search=False,
        global_minimum_proven=False)
    return result
