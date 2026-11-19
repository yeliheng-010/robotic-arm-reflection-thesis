"""重建观测序列、分配决策、实际动作和原物理判据。"""
from pathlib import Path
from loopstudy import audit as original
from loopstudy.actions import initial
from hardstudy.qualify import audit as qualify_audit
from hardstudy.intervention import audit as intervention_audit
from hardstudy.bridge import bound
from ap_common import ROOT,read,METHODS,MAX_ATTEMPTS,MAX_EXTRA,MAX_PHYSICAL
from ap_policy import observe,decide


def audit_trace(trace,reference):
    item,steps,decisions=trace['item'],trace['attempts'],trace['decisions']
    assert trace['method'] in METHODS and trace['status']=='completed' and trace['model'] is None
    assert trace['source']=='active_observation_rule_qualification'
    assert not trace['test_used'] and not trace['training_approved']
    assert 1<=len(steps)<=MAX_ATTEMPTS and len(decisions)<MAX_ATTEMPTS
    state,used=initial(),0
    with bound(item):
        for i,step in enumerate(steps):
            assert step['index']==i+1 and step['state']==state
            intervention_audit(step,item)
            original.physical(step,item,reference)
            if i<len(decisions):
                assert not step['success']
                observation=observe(step,item,method=trace['method'],used=used)
                used+=observation['extra_cost']
                d=decisions[i]
                assert d==decide(step,observation)
                state=d['selected']['state'] if d['selected'] else None
    assert used==trace['extra_observations'] and used<=MAX_EXTRA
    assert trace['success']==steps[-1]['success'] and not any(s['success'] for s in steps[:-1])
    if state is None:
        assert len(decisions)==len(steps) and not trace['success']
    else:
        assert len(decisions)==len(steps)-1 and (trace['success'] or len(steps)==MAX_ATTEMPTS)


def pair_check(traces):
    if not traces:
        return
    a,b=(traces[m] for m in METHODS)
    assert a['attempts'][0]==b['attempts'][0]
    for i,(sa,sb) in enumerate(zip(a['attempts'],b['attempts'])):
        if sa['state']!=sb['state']:
            continue
        ignored={'result_path','result_sha256'}
        assert {k:v for k,v in sa.items() if k not in ignored}=={k:v for k,v in sb.items() if k not in ignored}
        if i>=min(len(a['decisions']),len(b['decisions'])):
            continue
        oa,ob=(t['decisions'][i]['observation'] for t in (a,b))
        for x,y in zip(oa['samples'],ob['samples']):
            assert {k:v for k,v in x.items() if k!='source_sha256'}=={k:v for k,v in y.items() if k!='source_sha256'}


def audit_scene(value):
    scene=value['scene']
    q=read(ROOT/'qualification'/scene['id']/'result.json')
    qualify_audit(q,scene)
    assert value['status']=='completed' and value['eligible']==q['eligible']
    assert value['model'] is None and not value['test_used'] and not value['training_approved']
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
        successes={m:t['success'] for m,t in traces.items()},model_calls=0)
