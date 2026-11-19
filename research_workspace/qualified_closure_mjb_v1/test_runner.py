"""所有新增替身测试在Slurm运行，真实模型/数据/积分均阻断。"""
import os
import sys
import unittest
from pathlib import Path
from qualified_closure_dynamics_v1.protocol import save, sha, require
from qualified_closure_dynamics_v3.guarded_imports import zero_motion


def main():
    root = Path(__file__).resolve().parent
    source_hashes = {p.name: sha(p) for p in root.glob('*.py')}
    with zero_motion() as counts:
        from reflection.__main__ import bootstrap
        bootstrap()
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(
            'qualified_closure_mjb_v1.'+name) for name in
            (sys.argv[1:] or ['test_protocol', 'test_limits', 'test_worker', 'test_audit', 'test_resources']))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    require(source_hashes == {p.name: sha(p) for p in root.glob('*.py')}, 'Test sources changed while running')
    save(root / ('tests_'+os.environ['SLURM_JOB_ID']+'.json'),
         dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
              passed=result.wasSuccessful(), counts=counts, source_hashes=source_hashes))
    if not result.wasSuccessful() or any(counts.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
