"""独立重建决策、请求账本、状态映射和实际执行结果。"""
from unittest.mock import patch
from pathlib import Path
import numpy as np
from loopstudy import audit as physical_audit
from loopstudy.actions import initial
from cl_worker import bound,audit_row
from rc_common import ROOT,SOURCE,METHODS,ALIAS,MAX_ATTEMPTS,read
from rc_client import payload,check_response
from rc_policy import decide


def replay_event(event,messages):
    assert event['request']==payload(messages) and not event.get('service_failure')
    response=event['response']
    ledger=read(ROOT/'service/requests'/f"{response['id']}.json")
    assert ledger==dict(request=event['request'],response=response)
    try:
        text=check_response(response)
    except ValueError as error:
        assert event['invalid']==repr(error) and 'text' not in event
    else:
        assert event['text']==text and 'invalid' not in event
    return event


def check_step(step,source,plan):
    reference=read(source['step']['result_path'])['records'][0]
    layout=plan['layouts'][str(source['item']['seed'])]
    with bound(source['item'],layout):
        record,_=physical_audit.physical(step,source['item'],reference)
    actual=record['candidate_trace']['initial_body_xyz']
    for name,bid in source['geometry']['body_ids'].items():
        np.testing.assert_allclose(source['geometry']['positions'][name],actual[bid][:2],atol=1e-8,rtol=0)


def audit_trace(trace,source,plan):
    method=trace['method']
    steps,decisions=trace['attempts'],trace['decisions']
    assert method in METHODS and trace['item']==source['item']
    assert trace['source_index']==source['index'] and steps[0]==source['step']
    assert trace['status']=='completed' and trace['model']==(ALIAS if method=='model' else None)
    assert not trace['test_used'] and not trace['training_approved'] and trace['extra_observations']==0
    assert 1<=len(steps)<=MAX_ATTEMPTS and len(decisions)<MAX_ATTEMPTS
    state=initial()
    for i,step in enumerate(steps):
        assert step['index']==i+1 and step['state']==state
        check_step(step,source,plan)
        if i<len(decisions):
            assert not step['success']
            decision=decisions[i]
            with patch('rc_policy.generate',side_effect=lambda msgs:replay_event(decision['event'],msgs)):
                expected=decide(steps[:i+1],decisions[:i],method=method)
            assert decision==expected and not decision.get('service_failure')
            state=decision['selected']['state'] if decision['selected'] else None
    assert trace['success']==steps[-1]['success'] and not any(s['success'] for s in steps[:-1])
    if state is None:
        assert len(decisions)==len(steps) and not trace['success']
    else:
        assert len(decisions)==len(steps)-1 and (trace['success'] or len(steps)==MAX_ATTEMPTS)
    return dict(success=trace['success'],attempts=len(steps),new_physical=len(steps)-1,
        invalid=sum(d['selected'] is None for d in decisions),
        calls=[d['event']['response']['id'] for d in decisions if 'event' in d])


def audit_scene(index,manifest):
    source=manifest['rows'][index]
    plan=read(SOURCE/'plan.json')
    audit_row(source,plan)
    directory=ROOT/'tasks'/source['item']['id']
    methods={}
    paths=set()
    for method in METHODS:
        trace=read(directory/method/'result.json')
        assert trace['method']==method
        methods[method]=audit_trace(trace,source,plan)
        paths.update(Path(s['result_path']) for s in trace['attempts'][1:])
    actual={p for p in directory.glob('*/attempt_*/result.json')}
    assert actual==paths,'Unaccounted physical execution'
    return dict(passed=True,index=index,id=source['item']['id'],methods=methods,
        first_success=source['success'],arm=source['item']['arm'],new_physical=len(paths))
