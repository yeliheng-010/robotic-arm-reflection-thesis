"""对照原始结果审计完整分母，不把跳过或重复轨迹算成成功。"""
import sys
from collections import Counter
import numpy as np
from sd_config import ROOT, GROUPS
from sd_common import read, save, sha, verify


def task(index, manifest):
    item = manifest['items'][index]
    row = read(ROOT/'physics'/item['id']/'result.json')
    assert row['index']==index and row['item']==item
    assert row['manifest_sha256']==sha(ROOT/'manifest.json')
    assert row['model_calls']==0 and not row['test_used']
    check_qualification(row)
    steps = row['steps']
    if row['status']=='qualification_rejected':
        assert not row['qualified'] and not steps and not row['success']
        return row
    assert row['status']=='executed' and row['qualified'] and 1 <= len(steps) <= 3
    check_steps(steps)
    assert row['success']==steps[-1]['success'] and row['initial_audit']['same_initial_state']
    return row


def check_steps(steps):
    for index, step in enumerate(steps, 1):
        assert step['index']==index and sha(step['result_path'])==step['result_sha256']
        result = read(step['result_path'])
        assert result['success']==step['success']==result['records'][0]['accepted']


def check_qualification(row):
    folder = ROOT/'physics'/row['item']['id']/'qualification'
    static = read(folder/'result.json')
    assert static['rgb_sha256']==sha(folder/'rgb.png')
    assert static['sensor_sha256']==sha(folder/'sensor.npz')
    with np.load(folder/'sensor.npz') as arrays:
        roots = arrays['roots']
    for name, data in static['visibility'].items():
        count = int(np.count_nonzero(roots==static['body_ids'][name]))
        assert count==data['pixels']
        assert data['visible_fraction']==count/max(1, data['isolated_pixels'])
        assert data['qualified']==(count>=64 and data['visible_fraction']>=.70)
    visible = all(static['visibility'][row['item'][key]]['qualified'] for key in ('source','destination'))
    accepted = visible and static['calibration']['passed'] and static['geometry_accepted']
    assert row['qualified']==(accepted and static['compiled_check']['passed'])


def summarize(rows):
    metrics = {}
    for group in GROUPS:
        selected = [r for r in rows if r['item']['group']==group]
        executed = [r for r in selected if r['status']=='executed']
        failures = Counter((r['steps'][-1]['feedback'] or {}).get('error_type', 'unknown')
                           for r in executed if not r['success'])
        metrics[group] = dict(planned=len(selected), executed=len(executed),
            rejected=len(selected)-len(executed), success=sum(r['success'] for r in executed),
            first_success=sum(r['steps'][0]['success'] for r in executed),
            physical_attempts=sum(len(r['steps']) for r in executed), failures=dict(failures))
    return metrics


def main(phase):
    manifest = verify()
    indices = range(12) if phase=='smoke' else range(len(manifest['items']))
    rows = [task(index, manifest) for index in indices]
    result = dict(passed=True, complete=True, accounted=len(rows), metrics=summarize(rows),
                  model_calls=0, training_approved=False, test_used=False,
                  manifest_sha256=sha(ROOT/'manifest.json'))
    save(ROOT/f'{phase}_verification.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
