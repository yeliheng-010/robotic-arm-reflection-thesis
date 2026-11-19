"""阶段全量审计、负向篡改测试与开发晋级门槛。"""
import sys
from copy import deepcopy
from cm_common import ROOT, SHARDS, verify, read, save, sha
from cm_audit import development, validation
from run import indices
from report import metrics, write


def statuses(manifest, stage):
    phases = ['smoke','batch'] if stage=='final' else [stage]
    for phase in phases:
        for shard in range(SHARDS):
            value = read(ROOT/'stages'/phase/f'{shard}.json')
            expected = indices(manifest,phase)[shard::SHARDS]
            assert value['status']=='completed' and value['indices']==expected
            assert value['completed']==value['expected']==len(expected)


def reject(result, manifest, check, *, mutate):
    altered = deepcopy(result)
    mutate(altered)
    try:
        check(altered,manifest)
    except (AssertionError,ValueError,KeyError):
        return
    raise AssertionError('Tampering accepted')


def tamper(result, manifest, check, *, dev):
    reject(result,manifest,check,mutate=lambda r:r.update(test_used=True))
    reject(result,manifest,check,mutate=lambda r:r.update(training_approved=True))
    reject(result,manifest,check,mutate=lambda r:r.update(status='incomplete'))
    def change(value):
        step = value['steps']['geometry'] if dev else value['steps']['geometry'][-1]
        step['success'] = not step['success']
    reject(result,manifest,check,mutate=change)
    return 4


def rows_for(manifest, stage):
    dev = stage=='development'
    selected = indices(manifest,stage) if stage!='final' else list(range(80))
    items = [c['source']['item'] for c in manifest['cases']] if dev else manifest['validation_plan']['items']
    directory = ROOT/('development' if dev else 'validation')
    assert {items[i]['id'] for i in selected}=={p.name for p in directory.iterdir()}
    check = development if dev else validation
    rows = []
    for index in selected:
        result = read(directory/items[index]['id']/'result.json')
        assert result['index']==index
        rows.append(check(result,manifest))
        save(ROOT/f'{stage}_audit_progress.json',dict(completed=len(rows),expected=len(selected)))
    return rows,tamper(result,manifest,check,dev=dev)


def main(stage):
    manifest = verify()
    statuses(manifest,stage)
    rows,checks = rows_for(manifest,stage)
    value = dict(passed=True,complete=stage=='final',accounted=len(rows),rows=rows,metrics=metrics(rows),
        manifest_sha256=sha(ROOT/'manifest.json'),tamper_checks=checks,test_used=False,training_approved=False)
    if stage=='development':
        value['promote'] = bool(value['metrics']['gains']) and not value['metrics']['regressions']
    path = 'verification.json' if stage=='final' else f'gate_{stage}.json'
    save(ROOT/path,value)
    if stage!='smoke':
        write(value,stage=stage)
    print(value['metrics'],flush=True)


if __name__=='__main__':
    assert sys.argv[1] in ('development','smoke','final')
    main(sys.argv[1])
