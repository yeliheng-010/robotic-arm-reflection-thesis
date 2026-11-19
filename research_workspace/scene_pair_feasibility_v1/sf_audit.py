"""分别核对相机选取、物理执行与旧配置的开发配对结果。"""
from collections import Counter
from unittest.mock import patch
from sd_common import read, save, sha
import sd_audit
from pv_audit import audit_depth, audit_actions
from pv_protocol import verify as previous_verify
from pair_run import execution_audits
from sf_camera import framed, proposal, PROPOSAL_BUDGET
from sf_common import ROOT, verify


def selection(seed, manifest, previous):
    key = f'{seed}_varied_noisy'
    selected = manifest['configs'][key]
    source = previous['configs'][key]
    for field in ('bodies', 'appearance', 'sensor'):
        assert selected[field] == source[field]
    row = read(ROOT/'selection'/str(seed)/'selection.json')
    assert row['accepted'] == selected['camera_accepted']
    attempts = row['attempts']
    assert 1 <= len(attempts) <= PROPOSAL_BUDGET
    for index, attempt in enumerate(attempts):
        expected = source['camera'] if index == 0 else proposal(seed, index, boxes=row['settled_boxes'])
        assert attempt['index'] == index and attempt['camera'] == expected
        assert attempt['framing'] == framed(row['settled_boxes'], expected)
        assert not attempt['accepted'] or index == len(attempts)-1
    if row['accepted']:
        assert attempts[-1]['accepted'] and selected['camera'] == attempts[-1]['camera']
        assert attempts[-1]['framing']['passed'] and row['capture']['calibration']['passed']
    else:
        assert len(attempts) == PROPOSAL_BUDGET and not attempts[-1]['accepted']
    return row


def old_row(item):
    folder = ROOT.parent/'scene_pair_validation_v1'/'physics'/item['id']
    row = read(folder/'result.json')
    assert read(folder/'comparison.json')['result_sha256'] == sha(folder/'result.json')
    return row


def enhanced(item, manifest):
    folder = ROOT/'physics'/item['id']
    row, identity = read(folder/'result.json'), read(folder/'identity.json')
    config = manifest['configs'][f"{item['seed']}_{item['group']}"]
    assert row['item'] == identity['item'] == item
    assert identity['manifest_sha256'] == sha(ROOT/'manifest.json')
    assert identity['result_sha256'] == sha(folder/'result.json')
    if not config['camera_accepted']:
        assert row['status'] == 'camera_configuration_rejected' and not row['steps'] and not row['success']
        return row
    assert read(folder/'configuration.json') == config
    with patch.object(sd_audit, 'ROOT', ROOT):
        sd_audit.check_qualification(row)
    if row['qualified']:
        sd_audit.check_steps(row['steps'])
        assert row['success'] == row['steps'][-1]['success']
        audit_actions(row)
        execution_audits(row['steps'], config)
        for step in row['steps']:
            audit_depth(step, config)
    else:
        assert not row['steps'] and not row['success']
    assert row['model_calls'] == 0 and not row['test_used'] and not row['training_approved']
    return row


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
    selections = [selection(seed, manifest, previous) for seed in manifest['seeds']]
    rows = []
    for item in manifest['items']:
        old = old_row(item)
        new = old if item['group'] == 'baseline' else enhanced(item, manifest)
        rows.append(dict(item=item, old=old, new=new, reused_baseline=item['group'] == 'baseline'))
    metrics = {scene: summarize([r for r in rows if r['item']['group'] == scene])
               for scene in ('baseline', 'varied_noisy')}
    save(ROOT/'verification.json', dict(passed=True, complete=True, accounted=len(rows), metrics=metrics,
         cameras_accepted=sum(s['accepted'] for s in selections), baseline_reused=24,
         actual_new_attempts=metrics['varied_noisy']['attempts'], manifest_sha256=sha(ROOT/'manifest.json'),
         promotion_allowed=metrics['varied_noisy']['regressions'] == 0,
         model_calls=0, training_approved=False, test_used=False, split='used_seed_development'))
    save(ROOT/'paired_ledger.json', rows)
    print(metrics, flush=True)


if __name__ == '__main__':
    main()
