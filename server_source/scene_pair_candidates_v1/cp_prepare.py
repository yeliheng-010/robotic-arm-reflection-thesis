"""只将原始过滤耗尽的条件排入补救回放，保留全条件分母。"""
import unittest
from sd_common import read, save, sha
from cr_common import verify as source_verify
from cp_common import ROOT, SOURCE

EXHAUSTED = '所有候选均发生碰撞或夹爪内部为空'


def scan(row):
    matches = []
    for step in row['new']['steps']:
        assert sha(step['result_path']) == step['result_sha256']
        record = read(step['result_path'])['records'][0]
        error = record.get('error') or {}
        if error.get('message') == EXHAUSTED:
            assert error['error_type'] == 'no_grasp_candidate'
            matches.append(step['index'])
    return dict(id=row['item']['id'], changed=bool(matches), attempts=matches)


def main():
    tests = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tests.wasSuccessful() and not (ROOT/'manifest.json').exists()
    previous = source_verify()
    ledger = read(SOURCE/'paired_ledger.json')
    assert read(SOURCE/'verification.json')['passed']
    scans = [scan(row) for row in ledger]
    save(ROOT/'scan.json', scans)
    identities = dict(previous['identities'])
    identities.update({str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py','.sh','.sbatch')})
    identities.update({str(SOURCE/n): sha(SOURCE/n) for n in ('manifest.json','verification.json','paired_ledger.json')})
    identities.update({s['result_path']: s['result_sha256'] for r in ledger for s in r['new']['steps']})
    identities[str(ROOT/'scan.json')] = sha(ROOT/'scan.json')
    selected = [r['id'] for r in scans if r['changed']]
    save(ROOT/'manifest.json', dict(items=previous['items'], configs=previous['configs'], selected=selected,
         identities=identities, split='used_seed_development', model_calls=0, training_approved=False, test_used=False))
    save(ROOT/'preflight.json', dict(passed=True, tests=tests.testsRun, selected=selected,
         manifest_sha256=sha(ROOT/'manifest.json')))
    print(dict(selected=selected, accounted=len(scans)), flush=True)


if __name__ == '__main__':
    main()
