"""单次只读固定点诊断；零优化、零构造、零积分。"""
import os
from qualified_projection_diagnostic_v1.common import (
    ROOT, RUN, PARENT, read, save, sha, verify, loaded_sources, diagnostic_only, source_snapshot)
from qualified_projection_diagnostic_v1.geometry import SIDES, geometry_check, constraint_at
from qualified_projection_diagnostic_v1.numerics import diagnose, self_checks


def main():
    identities = verify()
    save(RUN / 'diagnostic_claim.json', dict(consumed=1, job=os.environ['SLURM_JOB_ID'],
         optimizer_budget=0, integration_budget=0))
    with diagnostic_only() as (optimizer_counts, motion_counts):
        try:
            tests = self_checks()
            prior = read(PARENT / 'run/result.json')
            geometry, values, parameters = geometry_check(prior)
            numeric = {side: diagnose(constraint_at(values, parameters, side=side), prior['solutions'][side])
                       for side in SIDES}
            scipy = source_snapshot(identities)
            loaded = loaded_sources(identities)
            assert not any(optimizer_counts.values()) and not any(motion_counts.values())
        except Exception as error:
            save(RUN / 'failure.json', dict(error=type(error).__name__ + ': ' + str(error),
                 optimizer_counts=optimizer_counts, motion_counts=motion_counts))
            raise
    verify()
    save(RUN / 'loaded_sources.json', loaded)
    result = dict(job=os.environ['SLURM_JOB_ID'], passed=True, tests=tests, geometry=geometry,
        numerics=numeric, scipy=scipy, verified_identities=len(identities),
        optimizer_counts=optimizer_counts, motion_counts=motion_counts,
        original_result_sha256=sha(PARENT / 'run/result.json'),
        unique_failure_cause_proven=False, optimizer_success_reinterpreted=False,
        candidate_created=False, full_scene_checked=False, dynamics_validated=False,
        production_ready=False, execution_authorized=False)
    save(RUN / 'result.json', result)
    save(RUN / 'inventory.json', {path.name: sha(path) for path in RUN.iterdir() if path.is_file()})
    print(dict(passed=True, geometry=geometry['saved_value_geometry_passed'], tests=tests,
               optimizer_counts=optimizer_counts, motion_counts=motion_counts), flush=True)


if __name__ == '__main__':
    main()
