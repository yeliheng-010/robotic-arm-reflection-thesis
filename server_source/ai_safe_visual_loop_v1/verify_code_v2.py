import os
import sys
import subprocess
import unittest
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import check_input
from sv_requests_v2 import original, decorate
from sv_common import ROOT, read, save, sha


def main():
    assert os.environ.get('SLURM_JOB_ID')
    previous = read(ROOT/'code_checks/verification.json')
    assert all(sha(p) == h for p,h in previous['identities'].items())
    target = ROOT/'code_checks_v2'
    target.mkdir(exist_ok=False)
    tested = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tested.wasSuccessful()
    for script in ('worker_v2.py', 'audit_v2.py'):
        subprocess.run([sys.executable, '-B', str(ROOT/script), '--help'], check=True)
    cases = read(ROOT.parent/'natural_qualified_pilot_v1/manifest.json')['cases']
    def build(branch, session, view):
        case = next(c for c in cases if c['item']['id'] == branch.ledger['item']['id'])
        return decorate(original(branch, session, view), case)
    with patch.object(check_input, 'build', build):
        check_input.run(target)
    files = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch', '.md')]
    save(target/'verification.json', dict(passed=True, tests=tested.testsRun,
        identities={str(p):sha(p) for p in files}, physical_attempts=0, model_calls=0))


if __name__ == '__main__':
    main()
