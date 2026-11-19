"""真实参数的固定点评价与阻断优化器的测试；不是求解入口。"""
import os
import unittest
from pathlib import Path
import numpy as np
from scipy.optimize._numdiff import approx_derivative
from qualified_projection_diagnostic_v1.common import (
    verify as verify_parent, loaded_sources, diagnostic_only, read, save, sha)
from qualified_initial_projection_v2.geometry import problem_for_side
from qualified_initial_projection_v2.problem import ANGLE_SCALE, CONSTRAINT_SCALE

ROOT = Path(__file__).resolve().parent
PROJECT, RUN = ROOT.parent, ROOT / 'prepared'


def verify():
    for name, digest in read(ROOT / 'BINDINGS.json').items():
        assert sha(PROJECT / name) == digest, name
    identities = verify_parent()
    assert not (ROOT / 'authorization.json').exists()
    assert not (ROOT / 'run').exists()
    return identities


def evaluate_point(problem, point, *, label):
    u = (point-problem.reference)/ANGLE_SCALE
    x = problem.angles(u)
    np.testing.assert_allclose(point, x, atol=1e-17, rtol=0)
    expected_objective = 0.5*np.sum(((point-problem.reference)/ANGLE_SCALE)**2)
    np.testing.assert_allclose(expected_objective, problem.objective(u), atol=1e-12, rtol=0)
    np.testing.assert_allclose((point-problem.reference)/ANGLE_SCALE, problem.gradient(u), atol=1e-12, rtol=0)
    np.testing.assert_allclose(problem.full_residual(point)[1:]/CONSTRAINT_SCALE,
                               problem.constraint(u), atol=1e-12, rtol=0)
    bounds = (-np.inf, np.inf) if label == 'original' else (problem.lower, problem.upper)
    numeric = approx_derivative(problem.constraint, u, method='3-point', abs_step=1e-3, bounds=bounds)
    explicit = problem.jacobian(u)
    np.testing.assert_allclose(explicit, numeric, atol=1e-7, rtol=1e-6)
    return dict(label=label, angles=x.tolist(), u=u.tolist(), objective=float(problem.objective(u)),
        full_residual=problem.full_residual(x).tolist(), jacobian=explicit.tolist(),
        jacobian_difference_max=float(np.max(np.abs(explicit-numeric))),
        geometry_search_performed=False)


def fixed_points():
    old = read(PROJECT / 'qualified_initial_projection_v1/run/result.json')
    diagnostic = read(PROJECT / 'qualified_projection_diagnostic_v1/run/result.json')
    original = read(PROJECT / 'qualified_initial_state_v1/run/result.json')
    rows = {}
    for index, side in enumerate(('right', 'left')):
        problem = problem_for_side(side)
        points = [('original', problem.reference), ('clipped', problem.angles(problem.initial)),
                  ('saved_attempt', np.asarray(old['solutions'][side]['angles']))]
        rows[side] = [evaluate_point(problem, point, label=label) for label, point in points]
        np.testing.assert_allclose(old['solutions'][side]['base_frame_residual'],
                                   rows[side][-1]['full_residual'], atol=1e-12, rtol=0)
        expected = np.asarray(diagnostic['numerics'][side]['complex_jacobian'])*ANGLE_SCALE
        np.testing.assert_allclose(expected, rows[side][-1]['jacobian'], atol=1e-10, rtol=1e-10)
        local = original['states']['after'][index]['local']
        expected_base = [-local[1], local[0], local[2]]
        np.testing.assert_allclose(expected_base, rows[side][0]['full_residual'], atol=1e-12, rtol=0)
    return rows


def tests():
    suite = unittest.defaultTestLoader.loadTestsFromNames([
        'qualified_initial_projection_v2.test_contract', 'qualified_initial_projection_v2.test_problem'])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise AssertionError('V2 tests failed')
    return dict(passed=result.testsRun, actual_optimizer_runs=0, optimizer_return_values='test_doubles')


def main():
    identities = verify()
    save(RUN / 'validation_claim.json', dict(consumed=1, job=os.environ['SLURM_JOB_ID'],
         optimizer_budget=0, integration_budget=0))
    with diagnostic_only() as (optimizer_counts, motion_counts):
        try:
            test_result = tests()
            rows = fixed_points()
            loaded = loaded_sources(identities)
            assert not any(optimizer_counts.values()) and not any(motion_counts.values())
        except Exception as error:
            save(RUN / 'failure.json', dict(error=type(error).__name__+': '+str(error),
                 optimizer_counts=optimizer_counts, motion_counts=motion_counts))
            raise
    verify()
    save(RUN / 'loaded_sources.json', loaded)
    save(RUN / 'result.json', dict(passed=True, job=os.environ['SLURM_JOB_ID'], tests=test_result,
        fixed_points=rows, verified_identities=len(identities), optimizer_counts=optimizer_counts,
        motion_counts=motion_counts, real_solver_convergence_validated=False,
        execution_authorized=False, candidate_created=False, production_ready=False))
    save(RUN / 'inventory.json', {p.name: sha(p) for p in RUN.iterdir() if p.is_file()})
    print(dict(passed=True, tests=test_result, optimizer_counts=optimizer_counts,
               motion_counts=motion_counts, real_solver_convergence_validated=False), flush=True)


if __name__ == '__main__':
    main()
