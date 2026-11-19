import os
import sys
import subprocess
import unittest
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import check_input
import sv_audit_attempt
from sv_requests_v2 import original, decorate
from sv_span_audit import context
from sv_common import ROOT, read, save, sha


def historical(target):
    source = ROOT.parent/'natural_span_pilot_v1'
    name = 'P0_963001_baseline'
    audit = read(source/'audits'/(name+'.json'))
    assert audit['passed'] and audit['manifest_sha256'] == sha(source/'manifest.json')
    assert all(sha(p) == h for p,h in audit['identities'].items())
    case = next(c for c in read(source/'manifest.json')['cases'] if c['item']['id'] == name)
    step = read(source/'cases'/name/'attempt_1/step.json')
    case['control'] = step['control']
    with context():
        result = sv_audit_attempt.inspect(case, step)
    assert result['contact']['self_contact_samples'] == 0
    save(target/'historical.json', dict(passed=True, source=name, geometry=result['geometry'],
        contact=result['contact'], physical_attempts=0, model_calls=0))


def main():
    assert os.environ.get('SLURM_JOB_ID')
    previous = read(ROOT/'code_checks_v2/verification.json')
    assert all(sha(p) == h for p,h in previous['identities'].items())
    target = ROOT/'code_checks_v3'
    target.mkdir(exist_ok=False)
    tested = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tested.wasSuccessful()
    for script in ('worker_v3.py', 'audit_v3.py'):
        subprocess.run([sys.executable, '-B', str(ROOT/script), '--help'], check=True)
    cases = read(ROOT.parent/'natural_qualified_pilot_v1/manifest.json')['cases']
    def build(branch, session, view):
        case = next(c for c in cases if c['item']['id'] == branch.ledger['item']['id'])
        return decorate(original(branch, session, view), case)
    with patch.object(check_input, 'build', build):
        check_input.run(target)
    historical(target)
    files = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch', '.md')]
    save(target/'verification.json', dict(passed=True, tests=tested.testsRun,
        identities={str(p):sha(p) for p in files}, physical_attempts=0, model_calls=0))


if __name__ == '__main__':
    main()
