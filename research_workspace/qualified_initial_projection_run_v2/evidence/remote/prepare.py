"""验证新增入口并登记本轮几何授权，不进行真实求解。"""
import os
import unittest
from qualified_projection_diagnostic_v1.common import diagnostic_only, loaded_sources
from qualified_initial_projection_run_v2.protocol import (
    ROOT, RUN, BUDGET, RULES_SHA, read, save, sha, require, verify)


def main():
    require(not RUN.exists() and not (ROOT / 'authorization.json').exists(), 'Already registered')
    identities = verify()
    with diagnostic_only() as (optimizer, motion):
        suite = unittest.defaultTestLoader.loadTestsFromName('qualified_initial_projection_run_v2.test_gates')
        tested = unittest.TextTestRunner(verbosity=2).run(suite)
        require(tested.wasSuccessful(), 'Gate tests failed')
        loaded = loaded_sources(identities)
        require(not any(optimizer.values()) and not any(motion.values()), 'Unexpected operation')
    verify()
    save(ROOT / 'prepared.json', dict(passed=True, tests_passed=tested.testsRun,
        job=os.environ['SLURM_JOB_ID'], verified_identities=len(identities),
        optimizer_counts=optimizer, motion_counts=motion, loaded_sources=loaded))
    save(ROOT / 'authorization.json', dict(kind='isolated_geometry_only',
        geometry_execution_authorized=True, dynamics_execution_authorized=False, budget=BUDGET,
        rules_sha256=RULES_SHA, bindings_sha256=sha(ROOT / 'BINDINGS.json'),
        prepared_sha256=sha(ROOT / 'prepared.json'),
        approval_reference='用户采纳建立一次性入口、每侧一次零积分求解及独立审计的建议'))
    print(dict(registered=True, tests=tested.testsRun, optimizer=optimizer, motion=motion), flush=True)


if __name__ == '__main__':
    main()
