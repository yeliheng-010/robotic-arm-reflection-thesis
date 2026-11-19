"""测试、离线影子判定后冻结定向回归，不重跑全量实验。"""
from pathlib import Path
import unittest
from sd_common import read, save, sha
from cp_common import verify as source_verify
from guard_policy import forbidden, release_reason

ROOT = Path(__file__).resolve().parent
PREVIOUS = ROOT.parent/'scene_pair_candidates_v1'
DIAGNOSTIC = ROOT.parent/'scene_pair_contact_diagnostic_v1'


def shadow():
    result = []
    for case in read(DIAGNOSTIC/'manifest.json')['cases']:
        item = case['item']
        import json
        rows = [json.loads(line) for line in (DIAGNOSTIC/'physics'/item['id']/'contacts.jsonl').read_text().splitlines()]
        hit = next((r for r in rows if any(forbidden(c, item['source']) for c in r['contacts'])), None)
        release = next((r for r in rows if r['action'] == 'open_gripper' and r['event'] == 'begin'), None)
        reason = None
        if release:
            evidence = dict(held=all(item['source'] in release['pads'][s] for s in ('left', 'right')),
                            actual=[release['tcp'][i][3] for i in range(3)],
                            expected=[release['command'][i][3] for i in range(3)])
            reason = release_reason(evidence)
        result.append(dict(id=item['id'], first_collision=hit['time'] if hit else None,
                           release_available=release is not None, release_reason=reason))
    return result


def cases(previous, ledger):
    selected = [r for r in ledger if r['item']['group'] == 'varied_noisy' and r['new']['success']]
    ids = ('961103_baseline_0', '961103_baseline_1', '961103_varied_noisy_0', '961104_varied_noisy_0')
    selected += [next(r for r in ledger if r['item']['id'] == name) for name in ids]
    result = []
    for row in selected:
        task_id = row['item']['id']
        step = row['new']['steps'][0]
        assert step['index'] == 1
        result.append(dict(id=task_id, item=row['item'], config=previous['configs'][task_id],
                           step=step, strict_contacts=True))
    release = next(r for r in result if r['id'] == '961104_varied_noisy_0')
    result.append(dict(release, id='961104_release_only', strict_contacts=False))
    return result


def main():
    tests = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tests.wasSuccessful()
    previous = source_verify()
    rows = shadow()
    for row in rows:
        if row['id'] in ('961103_baseline_0', '961107_varied_noisy_0'):
            assert row['first_collision'] is None and row['release_reason'] is None
    assert next(r for r in rows if r['id'] == '961104_varied_noisy_0')['release_reason'] == 'object_dropped'
    save(ROOT/'shadow.json', rows)
    ledger = read(PREVIOUS/'paired_ledger.json')
    identities = dict(previous['identities'])
    identities.update({str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.sbatch')})
    identities.update({str(DIAGNOSTIC/n): sha(DIAGNOSTIC/n) for n in ('manifest.json', 'final_audit.json')})
    save(ROOT/'manifest.json', dict(cases=cases(previous, ledger), identities=identities,
         source_manifest_sha256=sha(PREVIOUS/'manifest.json'), protocol='focused_guard_regression',
         training_approved=False, promotion_allowed=False))
    save(ROOT/'preflight.json', dict(passed=True, tests=tests.testsRun, manifest_sha256=sha(ROOT/'manifest.json')))
    print(rows, flush=True)


if __name__ == '__main__':
    main()
