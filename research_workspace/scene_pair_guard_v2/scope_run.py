"""范围修正仅重跑一个受影响分支；共享证据先核验。"""
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from sd_common import read, save, sha
import guard_worker
from guard_audit import trace
from guard_policy import forbidden as strict
from contact_policy import forbidden
from guard_scope import context

ROOT = Path(__file__).resolve().parent
PREVIOUS = ROOT.parent/'scene_pair_guard_v1'


def scan(case):
    folder = PREVIOUS/'physics'/case['id']
    rows = trace(folder/'contacts.jsonl')
    source = case['item']['source']
    changed = any(strict(c, source) != forbidden(c, source) for r in rows for c in r['contacts'])
    return dict(id=case['id'], changed=changed, trace_sha256=sha(folder/'contacts.jsonl'))


def prepare():
    tests = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tests.wasSuccessful()
    assert read(PREVIOUS/'verification.json')['passed']
    previous = read(PREVIOUS/'manifest.json')
    scans = [scan(case) for case in previous['cases']]
    selected = [r['id'] for r in scans if r['changed']]
    assert selected == ['961109_varied_noisy_0', '961104_varied_noisy_0']
    identities = dict(previous['identities'])
    identities.update({str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.sbatch')})
    identities.update({str(PREVIOUS/n): sha(PREVIOUS/n) for n in ('manifest.json', 'verification.json')})
    identities.update({str(PREVIOUS/'physics'/c['id']/n): sha(PREVIOUS/'physics'/c['id']/n)
                       for c in previous['cases'] for n in ('audit.json', 'guard.json', 'contacts.jsonl')})
    save(ROOT/'manifest.json', dict(cases=previous['cases'], scans=scans, selected=selected,
                                   identities=identities, tests=tests.testsRun))
    return read(ROOT/'manifest.json')


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = prepare()
    for path, digest in manifest['identities'].items():
        assert sha(path) == digest, path
    with patch.object(guard_worker, 'ROOT', ROOT), patch.object(guard_worker, 'guard_context', context):
        for case in manifest['cases']:
            if case['id'] in manifest['selected']:
                guard_worker.run(case)
    for path, digest in manifest['identities'].items():
        assert sha(path) == digest, path
    save(ROOT/'run_complete.json', dict(complete=True, actual_new_attempts=len(manifest['selected']),
                                       reused_cases=len(manifest['cases'])-len(manifest['selected']),
                                       manifest_sha256=sha(ROOT/'manifest.json')))


if __name__ == '__main__':
    main()
