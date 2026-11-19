"""分别核对原始噪声、有限补值、实际后果与共享未触发条件。"""
from pathlib import Path
from unittest.mock import patch
import numpy as np
from sd_common import read, save, sha
import sf_audit
from dr_common import ROOT, SOURCE, verify
from dr_scan import scan
from depth_estimate import estimate


def recovery(step):
    record = read(step['result_path'])['records'][0]
    row = record['depth_recovery']
    assert row['extra_observations'] == 0
    assert row['changed'] == any(e['accepted'] for e in row['events'])
    if not row['changed']:
        assert row['artifact'] is None
        return
    assert sha(row['artifact']) == row['sha256']
    noisy_path = Path(step['result_path']).parent/'attempt_1'/'depth_evidence.npz'
    with np.load(noisy_path) as arrays:
        expected = arrays['noisy'].copy()
    with np.load(row['artifact']) as arrays:
        np.testing.assert_array_equal(expected, arrays['raw'])
        for event in row['events']:
            actual = estimate(expected, arrays['roots'] == event['expected_id'], pixel=event['pixel_uv'])
            assert dict(actual, expected_id=event['expected_id']) == event
            if event['accepted']:
                u, v = event['pixel_uv']
                expected[v, u] = event['value_m']
        np.testing.assert_array_equal(expected, arrays['effective'])


def main():
    manifest = verify()
    source = read(SOURCE/'paired_ledger.json')
    scans = read(ROOT/'scan.json')
    assert scans == [scan(row) for row in source]
    rows = []
    for row in source:
        item, old = row['item'], row['new']
        reused = item['id'] not in manifest['selected']
        new = old
        if not reused:
            with patch.object(sf_audit, 'ROOT', ROOT):
                new = sf_audit.enhanced(item, manifest)
            for step in new['steps']:
                recovery(step)
        rows.append(dict(item=item, old=old, new=new, reused=reused))
    metrics = {scene: sf_audit.summarize([r for r in rows if r['item']['group'] == scene])
               for scene in ('baseline', 'varied_noisy')}
    save(ROOT/'verification.json', dict(passed=True, complete=True, accounted=len(rows), metrics=metrics,
         actual_new_attempts=sum(len(r['new']['steps']) for r in rows if not r['reused']),
         reused_conditions=sum(r['reused'] for r in rows),
         local_improvement=metrics['varied_noisy']['gains'] > 0 and metrics['varied_noisy']['regressions'] == 0,
         manifest_sha256=sha(ROOT/'manifest.json'), model_calls=0, training_approved=False, test_used=False))
    save(ROOT/'paired_ledger.json', rows)
    print(metrics, flush=True)


if __name__ == '__main__':
    main()
