"""模型请求全集、身份和原样回放门禁。"""
from copy import deepcopy
from cd_common import ROOT, verify, read, save, sha
from cd_client import check_response
from cd_records import tasks, audit_record


def reject(record, task, manifest, *, mutate):
    value = deepcopy(record)
    mutate(value)
    try:
        audit_record(value,task,manifest)
    except (AssertionError,ValueError,KeyError):
        return
    raise AssertionError('Tampering accepted')


def main():
    manifest = verify()
    progress = read(ROOT/'model_progress.json')
    assert progress['status']=='completed' and progress['completed']==progress['expected']==44
    rows, identifiers, files = [], [], set()
    for task in tasks(manifest):
        path = ROOT/'model_records'/f"{task['id']}.json"
        record = read(path)
        result = audit_record(record,task,manifest)
        rows.append(dict(task=task,result=result))
        identifiers.append(record['response']['id'])
        files.add(path)
    assert files == set((ROOT/'model_records').glob('*.json'))
    startup = read(ROOT/'model_startup.json')
    assert startup['passed'] and [r['index'] for r in startup['replay']]==[0,52]
    for row in startup['replay']:
        identifier = row['request_id']
        check_response(read(ROOT/'service/requests'/f'{identifier}.json')['response'])
        identifiers.append(identifier)
    assert len(identifiers)==len(set(identifiers))==46
    assert set(identifiers)=={p.stem for p in (ROOT/'service/requests').glob('*.json')}
    reject(record,task,manifest,mutate=lambda r:r['request'].update(temperature=1))
    reject(record,task,manifest,mutate=lambda r:r['response'].update(active_method='sft'))
    reject(record,task,manifest,mutate=lambda r:r['result'].update(valid=not r['result']['valid']))
    save(ROOT/'gate_model.json',dict(passed=True,manifest_sha256=sha(ROOT/'manifest.json'),
        task_calls=44,startup_calls=2,exact_replays=11,tamper_checks=3,rows=rows,
        identities={str(p):sha(p) for p in files|set((ROOT/'service/requests').glob('*.json'))}))
    print('PASS: 44 decisions, 11 exact replays, 46 ledger entries',flush=True)


if __name__ == '__main__':
    main()
