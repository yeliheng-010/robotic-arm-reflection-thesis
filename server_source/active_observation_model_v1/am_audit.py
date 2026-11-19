"""重放可见策略输入、模型账本、预算及物理判据，不额外调用模型。"""
from pathlib import Path
from itertools import combinations
from unittest.mock import patch
from loopstudy import audit as original
from loopstudy.actions import initial
from hardstudy.qualify import audit as qualify_audit
from hardstudy.intervention import audit as intervention_audit
from hardstudy.bridge import bound
from am_common import ROOT,read,METHODS,MODEL_METHODS,ALIAS,SOURCE_TAG,MAX_ATTEMPTS,MAX_EXTRA,MAX_PHYSICAL,MAX_CALLS
from am_client import payload,check_response
from am_policy import history_entry
from am_decision import decide


def check_event(event,messages):
    assert event['request']==payload(messages) and 'service_failure' not in event
    response=event['response']
    identifier=response['id']
    assert len(identifier)==32 and all(c in '0123456789abcdef' for c in identifier)
    assert read(ROOT/'service/requests'/f'{identifier}.json')==dict(request=event['request'],response=response)
    try:
        text=check_response(response)
    except ValueError as error:
        assert event['invalid']==repr(error) and 'text' not in event
    else:
        assert event['text']==text and 'invalid' not in event
    return event


def decision_check(d,step,*,item,method,used,history):
    events=[c['event'] for c in d['choices'] if 'event' in c]
    cursor=iter(events)
    def replay(messages):
        return check_event(next(cursor),messages)
    with patch('am_decision.generate',side_effect=replay):
        expected=decide(step,item,method=method,used=used,history=history)
    assert next(cursor,None) is None and d==expected
    assert not d['service_failure']
    return d['observation']['extra_cost']


def audit_trace(trace,reference):
    item,steps,decisions=trace['item'],trace['attempts'],trace['decisions']
    method=trace['method']
    assert method in METHODS and trace['status']=='completed' and trace['source']==SOURCE_TAG
    assert trace['model']==(ALIAS if method in MODEL_METHODS else None)
    assert not trace['test_used'] and not trace['training_approved']
    assert 1<=len(steps)<=MAX_ATTEMPTS and len(decisions)<MAX_ATTEMPTS
    state,used,history=initial(),0,[]
    with bound(item):
        for i,step in enumerate(steps):
            assert step['index']==i+1 and step['state']==state
            intervention_audit(step,item)
            original.physical(step,item,reference)
            if i:
                prev=decisions[i-1]
                history.append(history_entry(prev['choices'][-1]['context'],prev['selected'],step))
            if i<len(decisions):
                assert not step['success']
                d=decisions[i]
                used+=decision_check(d,step,item=item,method=method,used=used,history=history)
                state=d['selected']['state'] if d['selected'] else None
    assert used==trace['extra_observations'] and used<=MAX_EXTRA
    assert trace['success']==steps[-1]['success'] and not any(s['success'] for s in steps[:-1])
    calls=sum('event' in c for d in decisions for c in d['choices'])
    assert calls<=(MAX_CALLS if method in MODEL_METHODS else 0)
    if state is None:
        assert len(decisions)==len(steps) and not trace['success']
    else:
        assert len(decisions)==len(steps)-1 and (trace['success'] or len(steps)==MAX_ATTEMPTS)


def pair_check(traces):
    for a,b in combinations(traces.values(),2):
        assert a['attempts'][0]==b['attempts'][0]
        for sa,sb in zip(a['attempts'],b['attempts']):
            if sa['state']==sb['state']:
                ignored={'result_path','result_sha256'}
                assert {k:v for k,v in sa.items() if k not in ignored}=={k:v for k,v in sb.items() if k not in ignored}


def audit_scene(value):
    scene=value['scene']
    q=read(ROOT/'qualification'/scene['id']/'result.json')
    qualify_audit(q,scene)
    assert value['status']=='completed' and value['eligible']==q['eligible'] and value['source']==SOURCE_TAG
    assert not value['test_used'] and not value['training_approved']
    paths=[ROOT/'tasks'/scene['id']/m/'result.json' for m in METHODS] if q['eligible'] else []
    assert value['trajectories']==[str(p) for p in paths]
    traces={p.parent.name:read(p) for p in paths}
    item=dict(scene,id=scene['id']+'_qualification',arm='new_rule')
    for method,t in traces.items():
        assert t['item']==item and t['method']==method and t['attempts'][0]==q['steps'][1]
        audit_trace(t,read(q['steps'][0]['result_path'])['records'][0])
    pair_check(traces)
    executed={s['result_path'] for s in q['steps']}
    executed.update(s['result_path'] for t in traces.values() for s in t['attempts'])
    disk=set((ROOT/'tasks'/scene['id']).glob('**/attempt_*/result.json'))
    disk.update((ROOT/'qualification'/scene['id']).glob('[01]/result.json'))
    assert {str(p) for p in disk}==executed and len(executed)<=MAX_PHYSICAL
    return dict(id=scene['id'],passed=True,eligible=q['eligible'],qualification=q['status'],
        physical_executions=len(executed),trajectories=len(traces),
        extra_observations=sum(t['extra_observations'] for t in traces.values()),
        model_calls=sum('event' in c for t in traces.values() for d in t['decisions'] for c in d['choices']),
        invalid=sum(bool(d['invalid']) for t in traces.values() for d in t['decisions']),
        successes={m:t['success'] for m,t in traces.items()})
