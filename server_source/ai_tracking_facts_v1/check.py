import os
import unittest
from pathlib import Path
from f_common import read, save, sha
from tracking_facts import summarize

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'ai_route_bridge_v2'


def main():
    assert os.environ.get('SLURM_JOB_ID')
    suite = unittest.defaultTestLoader.discover(str(ROOT))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful()
    audit = read(SOURCE/'audit_962501.json')
    p = SOURCE/'cases/V0_962501_varied_noisy/attempt_1/telemetry.json'
    assert sha(p)==audit['identities'][str(p)]
    summary = summarize(read(p)['rows'])
    close = next(r for r in summary['actions'] if r['action']=='close_gripper')
    expected = read(ROOT.parent/'natural_tracking_audit_v1/result.json')['rows'][1]
    assert abs(close['last']['position_error_m']-expected['actual_target_difference_m'])<1e-12
    save(ROOT/'verification.json', dict(passed=True, tests=result.testsRun, physical_attempts=0,
        model_calls=0, training_ready=False, summary=summary,
        identities={str(p):sha(p), str(ROOT/'tracking_facts.py'):sha(ROOT/'tracking_facts.py')}))
    print(dict(passed=True, tests=result.testsRun, last_error_m=close['last']['position_error_m']), flush=True)


if __name__ == '__main__':
    main()
