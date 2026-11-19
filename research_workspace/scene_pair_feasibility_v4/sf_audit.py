"""分别核对相机选取、物理执行与旧配置的开发配对结果。"""
from collections import Counter
from unittest.mock import patch
from sd_common import read, save, sha
import sd_audit
from pv_audit import audit_depth, audit_actions
from pv_protocol import verify as previous_verify
from pair_run import execution_audits
from sf_selection_audit import selection
from sf_common import ROOT, verify, enhanced as enhanced_items


def old_row(item):
    folder = ROOT.parent/'scene_pair_validation_v1'/'physics'/item['id']
    row = read(folder/'result.json')
    assert read(folder/'comparison.json')['result_sha256'] == sha(folder/'result.json')
    return row


def enhanced(item, manifest):
    folder = ROOT/'physics'/item['id']
    row, identity = read(folder/'result.json'), read(folder/'identity.json')
    config = manifest['configs'][item['id']]
    assert row['item'] == identity['item'] == item
    assert identity['manifest_sha256'] == sha(ROOT/'manifest.json')
    assert identity['result_sha256'] == sha(folder/'result.json')
    assert row['model_calls'] == 0 and not row['test_used'] and not row['training_approved']
    if not config['camera_accepted']:
        assert row['status'] == 'camera_configuration_rejected' and not row['steps'] and not row['success']
        return row
    assert read(folder/'configuration.json') == config
    for path, digest in read(folder/'identities.json').items():
        assert sha(path) == digest
    with patch.object(sd_audit, 'ROOT', ROOT):
        sd_audit.check_qualification(row)
    audit_execution(row, config)
    return row


def audit_execution(row, config):
    if row['qualified']:
        assert row['status'] == 'executed' and 1 <= len(row['steps']) <= 3
        assert row['initial_audit']['same_initial_state']
        sd_audit.check_steps(row['steps'])
        assert row['success'] == row['steps'][-1]['success']
        audit_actions(row)
        execution_audits(row['steps'], config)
        for step in row['steps']:
            audit_depth(step, config)
    else:
        assert row['status'] == 'qualification_rejected' and not row['steps'] and not row['success']
    assert row['model_calls'] == 0 and not row['test_used'] and not row['training_approved']


def summarize(rows):
    counts = Counter(dict(planned=0, executed=0, rejected=0, success=0, old_success=0,
                          gains=0, regressions=0, attempts=0, first_success=0))
    failures = Counter()
    for row in rows:
        new, old = row['new'], row['old']
        counts.update(planned=1, executed=int(new['qualified']), rejected=int(not new['qualified']),
                      success=int(new['success']), old_success=int(old['success']),
                      gains=int(new['success'] and not old['success']),
                      regressions=int(not new['success'] and old['success']),
                      attempts=len(new['steps']),
                      first_success=int(bool(new['steps']) and new['steps'][0]['success']))
        if new['qualified'] and not new['success']:
            failures.update([new['steps'][-1]['feedback']['error_type']])
    return dict(counts, failures=dict(failures))


def main():
    manifest, previous = verify(), previous_verify()
    selections = [selection(item, manifest, previous) for item in enhanced_items(manifest)]
    rows = []
    for item in manifest['items']:
        old = old_row(item)
        if item['group'] == 'baseline':
            assert manifest['configs'][item['id']] == previous['configs'][f"{item['seed']}_baseline"]
        new = old if item['group'] == 'baseline' else enhanced(item, manifest)
        rows.append(dict(item=item, old=old, new=new, reused_baseline=item['group'] == 'baseline'))
    metrics = {scene: summarize([r for r in rows if r['item']['group'] == scene])
               for scene in ('baseline', 'varied_noisy')}
    save(ROOT/'verification.json', dict(passed=True, complete=True, accounted=len(rows), metrics=metrics,
         cameras_accepted=sum(s['accepted'] for s in selections), baseline_reused=24,
         actual_new_attempts=metrics['varied_noisy']['attempts'], manifest_sha256=sha(ROOT/'manifest.json'),
         promotion_allowed=(metrics['varied_noisy']['regressions'] == 0 and metrics['varied_noisy']['gains'] > 0),
         model_calls=0, training_approved=False, test_used=False, split='used_seed_development'))
    save(ROOT/'paired_ledger.json', rows)
    print(metrics, flush=True)


if __name__ == '__main__':
    main()
