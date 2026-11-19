"""全量复现原82输入；格式无效记入分母，工程错误阻止物理后继。"""
from collections import Counter
from copy import deepcopy
from od_common import ROOT,read,save,sha,verify,MAX_CALLS
from od_source import source_input
from od_records import tasks,load_record,audit_record
from od_prompts import eligible
from od_api import payload,check_response


def startup_check(startup):
    from od_common import PARENT
    folder=PARENT/'set_sft_v1'
    raw=read(folder/'eval.json')
    expected={r['index']:r['text'] for shard in range(3)
        for r in read(folder/'evaluation/before'/f'shard_{shard}/result.json')['rows'] if r['method']=='base'}
    assert [r['index'] for r in startup['replay']]==[0,52]
    for row in startup['replay']:
        value=read(ROOT/'service/requests'/f"{row['request_id']}.json")
        assert value['request']==payload(raw[row['index']]['messages'])
        assert check_response(value['response'])==expected[row['index']]


def aggregate(rows):
    out={}
    for r in rows:
        task,result=r['task'],r['result']
        key=task.get('variant','execute_'+str(task.get('level')))+'__'+task['row']['method']
        counter=out.setdefault(key,Counter())
        counter['total']+=1
        counter['valid']+=result['valid']
        counter['observe']+=result['action']=='OBSERVE'
        counter['probe_correct']+=result['correct'] is True
        missing=eligible(source_input(task['row'])['decision']['choices'][0]['context'])
        counter['missing']+=missing
        counter['observe_when_missing']+=missing and result['action']=='OBSERVE'
    return {k:dict(v) for k,v in out.items()}


def tamper(records):
    first=next(r for r in records if r['task'].get('variant')=='unified_first')
    changes={'prompt':lambda r:r['request']['messages'][1].update(content='{}'),
        'identity':lambda r:r['response']['identity'].update(adapter_enabled=True),
        'action':lambda r:r['result'].update(action='forged'),
        'row':lambda r:r['task']['row'].update(decision_index=99)}
    rejected=[]
    for name,mutate in changes.items():
        changed=deepcopy(first)
        mutate(changed)
        try:
            audit_record(changed,first['task'])
        except (AssertionError,ValueError,KeyError,IndexError):
            rejected.append(name)
        else:
            raise AssertionError('Accepted model tamper: '+name)
    return rejected


def audit():
    manifest=verify()
    assert read(ROOT/'model_progress.json')['status']=='completed'
    records=[load_record(t) for t in tasks(manifest)]
    assert {p.stem for p in (ROOT/'model_records').glob('*.json')}=={r['task']['id'] for r in records}
    ids=[r['response']['id'] for r in records]
    startup=read(ROOT/'model_startup.json')
    startup_check(startup)
    startup_ids=[r['request_id'] for r in startup['replay']]
    assert startup['passed'] and len(startup_ids)==2
    assert len(ids)==len(set(ids))==MAX_CALLS and not set(ids)&set(startup_ids)
    assert {p.stem for p in (ROOT/'service/requests').glob('*.json')}==set(ids+startup_ids)
    rejected=tamper(records)
    assert len(rejected)==4
    value=dict(passed=True,task_calls=len(ids),startup_calls=2,all_calls=len(ids)+2,
        original_replays=82,summary=aggregate(records),tamper_rejections=rejected,
        manifest_sha256=sha(ROOT/'manifest.json'),test_used=False,training_approved=False)
    save(ROOT/'model_verification.json',value)
    save(ROOT/'gate_model.json',dict(passed=True,manifest_sha256=value['manifest_sha256']))
    print(value,flush=True)
    return value


if __name__=='__main__':
    audit()
