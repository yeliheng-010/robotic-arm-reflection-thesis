"""冻结源码和观测扫描；只排入实际可能发生变化的条件。"""
import unittest
from sd_common import read, save, sha
from sf_common import verify as source_verify
from dr_common import ROOT, SOURCE
from dr_scan import scan


def main():
    assert not (ROOT/'manifest.json').exists()
    tests = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tests.wasSuccessful()
    previous = source_verify()
    assert read(SOURCE/'verification.json')['passed']
    ledger = read(SOURCE/'paired_ledger.json')
    scans = [scan(row) for row in ledger]
    save(ROOT/'scan.json', scans)
    identities = dict(previous['identities'])
    identities.update({str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch')})
    identities.update({str(SOURCE/name): sha(SOURCE/name) for name in ('paired_ledger.json', 'manifest.json', 'verification.json')})
    identities[str(ROOT/'scan.json')] = sha(ROOT/'scan.json')
    for item in scans:
        for trace in item['traces']:
            identities.update(trace['identities'])
    selected = [r['id'] for r in scans if r['changed']]
    save(ROOT/'manifest.json', dict(items=previous['items'], configs=previous['configs'], selected=selected,
         identities=identities, split='used_seed_development', model_calls=0, training_approved=False, test_used=False))
    save(ROOT/'preflight.json', dict(passed=True, tests=tests.testsRun, selected=selected,
         scanned_conditions=len(scans), scanned_observations=sum(len(r['traces']) for r in scans),
         manifest_sha256=sha(ROOT/'manifest.json')))
    print(dict(selected=selected, accounted=len(scans)), flush=True)


if __name__ == '__main__':
    main()
