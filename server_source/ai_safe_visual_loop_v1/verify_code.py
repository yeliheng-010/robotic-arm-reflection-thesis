import os
import sys
import subprocess
import unittest
from reflection.__main__ import bootstrap
bootstrap()
from sv_common import ROOT, save, sha
from check_input import run


def main():
    assert os.environ.get('SLURM_JOB_ID')
    target = ROOT/'code_checks'
    target.mkdir(exist_ok=False)
    tested = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tested.wasSuccessful()
    for script in ('worker.py', 'audit.py'):
        subprocess.run([sys.executable, '-B', str(ROOT/script), '--help'], check=True)
    run(target)
    files = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch', '.md')]
    save(target/'verification.json', dict(passed=True, tests=tested.testsRun,
        identities={str(p):sha(p) for p in files}, physical_attempts=0, model_calls=0))


if __name__ == '__main__':
    main()
