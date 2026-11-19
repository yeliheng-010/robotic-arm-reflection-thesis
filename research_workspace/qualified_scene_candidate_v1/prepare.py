"""只导入实际模块、测试阻断器和绑定来源，不创建场景。"""
import os
import unittest
from qualified_scene_candidate_v1.guard import no_motion, require_no_motion
from qualified_scene_candidate_v1 import worker, audit
from qualified_scene_candidate_v1.common import ROOT, RUN, verify, loaded_sources, save, sha, require


def main():
    require(not RUN.exists() and not (ROOT / 'prepared.json').exists(), 'Already prepared')
    identities = verify()
    tests = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
        'qualified_scene_candidate_v1.test_gate'))
    require(tests.wasSuccessful(), 'Gate tests failed')
    with no_motion() as counts:
        loaded = loaded_sources(identities)
        require_no_motion(counts)
    verify()
    save(ROOT / 'prepared.json', dict(passed=True, job=os.environ['SLURM_JOB_ID'], tests=tests.testsRun,
        counts=counts, loaded_sources=loaded, verified_identities=len(identities),
        bindings_sha256=sha(ROOT / 'BINDINGS.json'), initialization_budget=0, integration_budget=0))
    print(dict(passed=True, tests=tests.testsRun, counts=counts, files=len(loaded)), flush=True)


if __name__ == '__main__':
    main()
