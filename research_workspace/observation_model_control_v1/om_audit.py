"""重建测量、模型请求和物理结果，核验规则复现与模型身份。"""
from pathlib import Path
from loopstudy import audit as original
from loopstudy.actions import initial,choose_rule
from hardstudy.qualify import audit as qualify_audit
from hardstudy.intervention import audit as intervention_audit
from hardstudy.bridge import bound
from om_common import ROOT,read,METHODS,MAX_ATTEMPTS,MAX_EXTRA,MAX_PHYSICAL,ALIASES
from om_policy import observe,inputs,prompt,selection
from om_client import payload_for
from om_compare import compare_scene


def decision_check(d,step,*,method,used):
    observed=observe(step,d['_item'],method=method,used=used)
    base=inputs(step,observed)
    assert all(d[k]==v for k,v in base.items())
    assert d['method']==method and d['source']=='observation_processing_selector_control'
    assert d['model']==(ALIASES['base'] if method.startswith('base_') else None)
    assert not d.get('service_failure')
    rows=d['candidates']
    if not rows:
        assert d['selected'] is None and d['invalid']=='Candidate set exhausted' and 'event' not in d
    elif method.startswith('rule_'):
        assert 'event' not in d and 'invalid' not in d
        assert d['selected']==choose_rule(rows,d['before'],report=d['feedback'])
    else:
        event=d['event']
        assert event['request']==payload_for('base',prompt(d))
        response=event['response']
        identifier=response['id']
        assert len(identifier)==32 and all(c in '0123456789abcdef' for c in identifier)
        assert read(ROOT/'service/requests'/f'{identifier}.json')==dict(request=event['request'],response=response)
        selected,invalid=selection(event,rows)
        assert d['selected']==selected and d.get('invalid')==invalid
    return observed['extra_cost']


def audit_trace(trace,reference):
    item,steps,decisions=trace['item'],trace['attempts'],trace['decisions']
    method=trace['method']
    assert method in METHODS and trace['status']=='completed'
    assert trace['model']==(ALIASES['base'] if method.startswith('base_') else None)
    assert trace['source']=='observation_processing_selector_control'
    assert not trace['test_used'] and not trace['training_approved']
    assert 1<=len(steps)<=MAX_ATTEMPTS and len(decisions)<MAX_ATTEMPTS
    state,used=initial(),0
    with bound(item):
        for index,step in enumerate(steps):
            assert step['index']==index+1 and step['state']==state
            intervention_audit(step,item)
            original.physical(step,item,reference)
            if index<len(decisions):
                assert not step['success']
                d=decisions[index]
                used+=decision_check(dict(d,_item=item),step,method=method,used=used)
                state=d['selected']['state'] if d['selected'] else None
    assert used==trace['extra_observations'] and used<=MAX_EXTRA
    assert trace['success']==steps[-1]['success'] and not any(s['success'] for s in steps[:-1])
    if state is None:
        assert len(decisions)==len(steps) and not trace['success']
    else:
        assert len(decisions)==len(steps)-1
        assert trace['success'] or len(steps)==MAX_ATTEMPTS


def trajectories(value,q):
    scene=value['scene']
    item=dict(scene,id=scene['id']+'_qualification',arm='new_rule')
    paths=[ROOT/'tasks'/scene['id']/m/'result.json' for m in METHODS] if q['eligible'] else []
    assert value['trajectories']==[str(p) for p in paths]
    traces={p.parent.name:read(p) for p in paths}
    for method,t in traces.items():
        assert t['item']==item and t['method']==method and t['attempts'][0]==q['steps'][1]
        audit_trace(t,read(q['steps'][0]['result_path'])['records'][0])
    return traces


def audit_scene(value):
    scene=value['scene']
    q=read(ROOT/'qualification'/scene['id']/'result.json')
    qualify_audit(q,scene)
    assert value['status']=='completed' and value['eligible']==q['eligible']
    assert value['source']=='observation_processing_selector_control'
    assert not value['test_used'] and not value['training_approved']
    traces=trajectories(value,q)
    paths={s['result_path'] for s in q['steps']}
    paths.update(s['result_path'] for t in traces.values() for s in t['attempts'])
    disk=set((ROOT/'tasks'/scene['id']).glob('**/attempt_*/result.json'))
    disk.update((ROOT/'qualification'/scene['id']).glob('[01]/result.json'))
    assert {str(p) for p in disk}==paths and len(paths)<=MAX_PHYSICAL
    comparisons=compare_scene(scene,q,traces)
    return dict(id=scene['id'],passed=True,eligible=q['eligible'],qualification=q['status'],
        physical_executions=len(paths),trajectories=len(traces),comparisons=comparisons,
        model_calls=sum('event' in d for t in traces.values() for d in t['decisions']),
        invalid=sum('invalid' in d for t in traces.values() for d in t['decisions']),
        extra_observations=sum(t['extra_observations'] for t in traces.values()),
        successes={m:t['success'] for m,t in traces.items()})
