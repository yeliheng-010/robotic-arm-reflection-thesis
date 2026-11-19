"""共享前缀与相同路径候选条件下，仅核对第三次的排序干预。"""
from sd_common import read, save, sha
from sf_audit import audit_execution, summarize, old_row
from dr_audit import recovery
from cr_common import ROOT, SOURCE, verify
from cr_prepare import scan


def branch(row, manifest):
    item, old = row['item'], row['new']
    folder = ROOT/'physics'/item['id']
    new = read(folder/'result.json')
    identity = read(folder/'identity.json')
    assert identity['manifest_sha256'] == sha(ROOT/'manifest.json')
    assert identity['result_sha256'] == sha(folder/'result.json')
    assert new['item'] == item and new['steps'][:2] == old['steps'][:2]
    assert new['decisions'] == old['decisions']
    audit_execution(new, manifest['configs'][item['id']])
    a = read(old['steps'][2]['result_path'])['records'][0]
    b = read(new['steps'][2]['result_path'])['records'][0]
    for field in ('parameters', 'candidate_trace', 'stable_voxel_grid'):
        assert a[field] == b[field], field
    before, after = a['motion_extension'], b['motion_extension']
    assert before['context'] == after['context']
    assert {r['id']: r for r in before['candidates']} == {r['id']: r for r in after['candidates']}
    expected = next(r for r in read(ROOT/'scan.json') if r['id'] == item['id'])['after']
    assert after['candidates'][after['selected']]['id'] == expected
    recovery(new['steps'][2])
    return new


def main():
    manifest = verify()
    source = read(SOURCE/'paired_ledger.json')
    assert read(ROOT/'scan.json') == [scan(row) for row in source]
    rows = []
    for row in source:
        reused = row['item']['id'] not in manifest['selected']
        new = row['new'] if reused else branch(row, manifest)
        rows.append(dict(item=row['item'], old=row['new'], new=new, reused=reused))
    metrics = {scene: summarize([r for r in rows if r['item']['group'] == scene])
               for scene in ('baseline', 'varied_noisy')}
    reference = summarize([dict(r, old=old_row(r['item'])) for r in rows if r['item']['group'] == 'varied_noisy'])
    save(ROOT/'verification.json', dict(passed=True, complete=True, accounted=len(rows), metrics=metrics,
         original_enhanced_comparison=reference, actual_new_attempts=len(manifest['selected']),
         shared_prefix_attempts=2*len(manifest['selected']), reused_conditions=sum(r['reused'] for r in rows),
         promotion_allowed=reference['gains'] > 0 and reference['regressions'] == 0,
         manifest_sha256=sha(ROOT/'manifest.json'), model_calls=0, training_approved=False, test_used=False))
    save(ROOT/'paired_ledger.json', rows)
    print(dict(metrics=metrics, reference=reference), flush=True)


if __name__ == '__main__':
    main()
