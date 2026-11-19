"""事后追加只读审计；不修改冻结协议、选择动作或物理结果。"""
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
from sd_common import read, save, sha, verify, config_for
from sd_config import ROOT, SEEDS
from sd_audit import task, summarize
from sd_physics import check_initial
from loopstudy.actions import initial
from rc_policy import decide


def inspect_record(step, item):
    raw = read(step['result_path'])
    record = raw['records'][0]
    assert raw['source']==item['source'] and raw['destination']==item['destination']
    assert raw['seed']==item['seed'] and raw['scene_jitter_m']==0
    assert raw['perception']=='simulation' and raw['segmentation']=='simulation'
    assert record['executor_state']==step['state']
    assert record['parameters']==step['state']['parameters']
    assert record['accepted']==record['physical_success']==step['success']
    if step['success']:
        evaluation = record['evaluation']
        assert all(evaluation[key] for key in ('inside_xy','inside_z','supported','settled'))
    return record


def inspect_row(row, manifest):
    item = manifest['items'][row['index']]
    assert item==row['item']
    steps, decisions = row['steps'], row['decisions']
    if not steps:
        return []
    assert steps[0]['state']==initial()
    records = [inspect_record(step, item) for step in steps]
    for index, decision in enumerate(decisions):
        expected = decide(steps[:index+1], decisions[:index], method='rule')
        assert expected==decision
        if index+1 < len(steps):
            assert decision['selected']['state']==steps[index+1]['state']
    static = read(ROOT/'physics'/item['id']/'qualification'/'result.json')
    check_initial(steps, config_for(item, manifest), static)
    return records


def tamper_checks(row, manifest):
    altered = deepcopy(row)
    altered['steps'][0]['state']['parameters']['lift_height'] += .01
    wrong_identity = deepcopy(row)
    wrong_identity['item']['seed'] += 1
    wrong_success = deepcopy(row)
    wrong_success['steps'][0]['success'] = not wrong_success['steps'][0]['success']
    checks = []
    for name, value in [('parameters',altered),('identity',wrong_identity),('success',wrong_success)]:
        try:
            inspect_row(value, manifest)
        except AssertionError:
            checks.append(name)
        else:
            raise AssertionError('Tamper was accepted: '+name)
    return checks


def paired(rows):
    lookup = {(r['item']['seed'],r['item']['group'],r['item']['source']):r for r in rows}
    results = []
    for seed in SEEDS:
        for source in ('RedBlock','PurpleCapsule'):
            for before, after in (('baseline','appearance'),('layout_camera','combined')):
                a, b = lookup[(seed,before,source)], lookup[(seed,after,source)]
                same = (a['qualified']==b['qualified'] and a['success']==b['success']
                        and [s['state'] for s in a['steps']]==[s['state'] for s in b['steps']])
                assert same, 'Appearance changed physical behavior'
                results.append(dict(seed=seed,source=source,pair=[before,after],same=same))
    return results


def main():
    manifest = verify()
    final = read(ROOT/'final_verification.json')
    rows = [task(index, manifest) for index in range(len(manifest['items']))]
    for row in rows:
        inspect_row(row, manifest)
    assert summarize(rows)==final['metrics']
    successes = [row for row in rows if row['steps'] and row['steps'][0]['success']]
    checks = tamper_checks(successes[0], manifest)
    result = dict(passed=True,complete=True,accounted=len(rows),tamper_rejected=checks,
        appearance_pairs=paired(rows),source_sha256=sha(__file__),
        manifest_sha256=sha(ROOT/'manifest.json'),scope='posthoc_read_only_execution_audit')
    save(ROOT/'delivery_verification.json', result)
    print('DELIVERY AUDIT PASSED', len(rows), 'conditions', len(result['appearance_pairs']), 'pairs', flush=True)


if __name__ == '__main__':
    main()
