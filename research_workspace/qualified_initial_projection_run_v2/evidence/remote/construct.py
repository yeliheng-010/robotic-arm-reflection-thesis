"""每侧一次真实SLSQP；无模型构造或积分。"""
import os
import numpy as np
from unittest.mock import patch
from scipy import optimize
from qualified_closure_dynamics_v3.guarded_imports import zero_motion
from qualified_projection_diagnostic_v1.common import loaded_sources
from qualified_initial_projection_v2.geometry import problem_for_side
from qualified_initial_projection_v2.solver import solve_side
from qualified_initial_projection_run_v2.protocol import (
    ROOT, RUN, read, save, sha, require, verify, authorization, claim)
from qualified_initial_projection_run_v2.state import SIDES, assemble


def solve_once(side, auth):
    claim(auth, RUN, name=side)
    problem = problem_for_side(side)
    original, calls = optimize.minimize, []
    def once(fun, initial, **kwargs):
        require(not calls, 'Repeated optimizer call')
        require(kwargs['method'] == 'SLSQP', 'Unexpected optimizer')
        require(kwargs['options'] == dict(maxiter=200, ftol=1e-14, disp=False), 'Options changed')
        require(callable(kwargs['constraints'][0]['jac']), 'Missing explicit Jacobian')
        calls.append(side)
        return original(fun, initial, **kwargs)
    with patch.object(optimize, 'minimize', once):
        result = solve_side(problem.reference, np.column_stack([problem.low, problem.high]),
                            residual=problem.residual)
    require(len(calls) == 1 and result['attempts'] == 1, 'Wrong optimizer budget')
    result['actual_optimizer_calls'] = len(calls)
    save(RUN / (side+'_result.json'), result)
    return result


def main():
    identities = verify()
    auth = authorization()
    claim(auth, RUN, name='construction')
    with zero_motion() as counts:
        try:
            solutions = {side: solve_once(side, auth) for side in SIDES}
            arrays, result = assemble(solutions)
            loaded = loaded_sources(identities)
            require(not any(counts.values()), 'Unexpected model/integration')
            verify()
            if arrays is not None:
                with (RUN / 'candidate_state.npz').open('xb') as stream:
                    np.savez_compressed(stream, **arrays)
                    stream.flush()
                    os.fsync(stream.fileno())
            result.update(solutions=solutions, job=os.environ['SLURM_JOB_ID'], counts=counts,
                verified_identities=len(identities), full_scene_checked=False, production_ready=False,
                dynamics_validated=False, dynamics_execution_authorized=False)
            save(RUN / 'loaded_sources.json', loaded)
            save(RUN / 'result.json', result)
        except Exception as error:
            save(RUN / 'failure.json', dict(error=type(error).__name__+': '+str(error), counts=counts))
            raise
    save(RUN / 'inventory.json', {p.name: sha(p) for p in RUN.iterdir() if p.is_file()})
    print(dict(candidate_created=result['candidate_created'], counts=counts), flush=True)


if __name__ == '__main__':
    main()
