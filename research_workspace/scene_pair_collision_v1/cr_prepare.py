"""由既有第三次路径检查证明排序是否改变实际选中姿态。"""
import unittest
from sd_common import read, save, sha
from dr_common import verify as source_verify
from collision_policy import eligible, ordered
from cr_common import ROOT, SOURCE


def selected_id(rows):
    return next((r['id'] for r in rows if r['feasible']), None)


def scan(row):
    steps = row['new']['steps']
    result = dict(id=row['item']['id'], changed=False)
    if len(steps) != 3 or not eligible(steps[1]['feedback']):
        return result
    step = steps[2]
    assert sha(step['result_path']) == step['result_sha256']
    motion = read(step['result_path'])['records'][0]['motion_extension']
    assert motion['active']
    before, after = selected_id(motion['candidates']), selected_id(ordered(motion['candidates']))
    return dict(result, changed=before != after, before=before, after=after,
                result_path=step['result_path'], result_sha256=step['result_sha256'])


def main():
    tests = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tests.wasSuccessful() and not (ROOT/'manifest.json').exists()
    previous = source_verify()
    ledger = read(SOURCE/'paired_ledger.json')
    assert read(SOURCE/'verification.json')['passed']
    scans = [scan(row) for row in ledger]
    save(ROOT/'scan.json', scans)
    identities = dict(previous['identities'])
    for row in ledger:
        for step in row['new']['steps']:
            assert sha(step['result_path']) == step['result_sha256']
            identities[step['result_path']] = step['result_sha256']
    identities.update({str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch')})
    identities.update({str(SOURCE/n): sha(SOURCE/n) for n in ('manifest.json','verification.json','paired_ledger.json')})
    identities.update({r['result_path']: r['result_sha256'] for r in scans if 'result_path' in r})
    identities[str(ROOT/'scan.json')] = sha(ROOT/'scan.json')
    selected = [r['id'] for r in scans if r['changed']]
    save(ROOT/'manifest.json', dict(items=previous['items'], configs=previous['configs'], selected=selected,
         identities=identities, split='used_seed_development', model_calls=0, training_approved=False, test_used=False))
    save(ROOT/'preflight.json', dict(passed=True, tests=tests.testsRun, selected=selected,
         manifest_sha256=sha(ROOT/'manifest.json')))
    print(scans, flush=True)


if __name__ == '__main__':
    main()
