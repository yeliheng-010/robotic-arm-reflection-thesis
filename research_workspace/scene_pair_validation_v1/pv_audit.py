"""核对真实执行与传感输入；共享前缀不重复计入物理尝试。"""
from collections import Counter
from unittest.mock import patch
import numpy as np
from sd_common import read, save, sha
import sd_audit
from diversity.noise import corrupt_depth
from drop_recovery import enabled
from rc_policy import decide
from pair_run import execution_audits
from pv_protocol import ROOT, SCENES, verify


def audit_depth(step, config):
    record = read(step['result_path'])['records'][0]
    sensor = record['domain_randomization']
    assert sensor['level'] == config['group']
    path = step['result_path'].replace('result.json', 'attempt_1/depth_evidence.npz')
    with np.load(path) as arrays:
        clean, actual = arrays['clean'], arrays['noisy']
    seed = np.random.SeedSequence([config['seed'], 301, step['index'], 0])
    expected, stats = corrupt_depth(clean, config['sensor'], seed=seed)
    np.testing.assert_array_equal(expected, actual)
    for key, value in stats.items():
        assert value == sensor['sensor_frames'][0][key]
    assert record['physical_success'] == record['accepted'] == step['success']
    return record


def audit_actions(row):
    steps, decisions = row['steps'], row['decisions']
    for index, decision in enumerate(decisions):
        assert decision == decide(steps[:index+1], decisions[:index], method='rule')
        if index+1 < len(steps):
            assert decision['selected']['state'] == steps[index+1]['state']


def audit_branch(row, comparison, config):
    old, steps = comparison['legacy'], row['steps']
    branched = len(steps) == 3 and enabled(index=3, report=steps[1]['feedback'])
    assert old['shared'] == (not branched)
    if not branched:
        assert old['success'] == row['success'] and old['extra_attempts'] == 0
        return
    step = old['step']
    assert step['index'] == 3 and sha(step['result_path']) == step['result_sha256']
    a = audit_depth(steps[2], config)
    b = audit_depth(step, config)
    for key in ('candidate_trace', 'domain_randomization', 'parameters'):
        assert a[key] == b[key]
    assert a['motion_extension']['active'] and not b['motion_extension']['active']
    assert old['success'] == step['success'] and old['extra_attempts'] == 1
    execution_audits([step], config)


def task(index, manifest):
    item = manifest['items'][index]
    folder = ROOT/'physics'/item['id']
    row, comparison = read(folder/'result.json'), read(folder/'comparison.json')
    config = manifest['configs'][f"{item['seed']}_{item['group']}"]
    assert row['item'] == comparison['item'] == item and comparison['index'] == index
    assert comparison['manifest_sha256'] == sha(ROOT/'manifest.json')
    assert comparison['result_sha256'] == sha(folder/'result.json')
    assert read(folder/'configuration.json') == config
    for path, digest in read(folder/'identities.json').items():
        assert sha(path) == digest
    with patch.object(sd_audit, 'ROOT', ROOT):
        sd_audit.check_qualification(row)
    assert row['model_calls'] == 0 and not row['test_used'] and not row['training_approved']
    if not row['qualified']:
        assert row['status'] == 'qualification_rejected' and not row['steps'] and not row['success']
    else:
        assert row['status'] == 'executed' and 1 <= len(row['steps']) <= 3
        sd_audit.check_steps(row['steps'])
        assert row['success'] == row['steps'][-1]['success']
        assert row['initial_audit']['same_initial_state']
        for step in row['steps']:
            audit_depth(step, config)
        audit_actions(row)
        execution_audits(row['steps'], config)
    audit_branch(row, comparison, config)
    assert comparison['new_success'] == row['success']
    return dict(row, comparison=comparison)


def group_metrics(selected):
    executed = [r for r in selected if r['qualified']]
    counts = Counter(dict(success=0, legacy_success=0, gains=0, regressions=0,
                          first_success=0, main_attempts=0, branch_attempts=0))
    for row in executed:
        old, success = row['comparison']['legacy'], row['success']
        counts.update(success=int(success), legacy_success=int(old['success']),
                      gains=int(success and not old['success']),
                      regressions=int(not success and old['success']),
                      first_success=int(row['steps'][0]['success']),
                      main_attempts=len(row['steps']), branch_attempts=old['extra_attempts'])
    failures = Counter(r['steps'][-1]['feedback']['error_type'] for r in executed if not r['success'])
    return dict(planned=len(selected), executed=len(executed), rejected=len(selected)-len(executed),
                **counts, failures=dict(failures))


def summarize(rows):
    return {scene: group_metrics([r for r in rows if r['item']['group'] == scene]) for scene in SCENES}


def main():
    manifest = verify()
    rows = [task(i, manifest) for i in range(len(manifest['items']))]
    metrics = summarize(rows)
    result = dict(passed=True, complete=True, accounted=len(rows), metrics=metrics,
                  manifest_sha256=sha(ROOT/'manifest.json'), model_calls=0,
                  training_approved=False, test_used=False,
                  promotion_allowed=all(m['regressions'] == 0 for m in metrics.values()))
    save(ROOT/'verification.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    main()
