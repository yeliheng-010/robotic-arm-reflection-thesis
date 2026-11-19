"""重建观测、预算、规则选择和原始物理；有限分支不放宽成功判据。"""
from pathlib import Path
from loopstudy import audit as original
from loopstudy.actions import initial
from hardstudy.qualify import audit as qualify_audit
from hardstudy.intervention import audit as intervention_audit
from hardstudy.bridge import bound
from pilot import ROOT,read,MAX_PHYSICAL,MAX_ATTEMPTS,MAX_EXTRA
from policy import modes,observe,decide,branch_target


def audit_trace(trace,reference):
    item,steps,decisions=trace['item'],trace['attempts'],trace['decisions']
    assert trace['status']=='completed' and trace['model'] is None
    assert trace['source']=='synthetic_sensor_rule_qualification'
    assert not trace['test_used'] and not trace['training_approved']
    assert trace['mode'] in modes(item)
    assert 1<=len(steps)<=MAX_ATTEMPTS[item['mechanism']]
    assert len(decisions)<=MAX_ATTEMPTS[item['mechanism']]-1
    state,used=initial(),0
    with bound(item):
        for index,step in enumerate(steps):
            assert step['index']==index+1 and step['state']==state
            intervention_audit(step,item)
            original.physical(step,item,reference)
            if index<len(decisions):
                assert not step['success']
                d=decisions[index]
                observation=observe(step,item,mode=trace['mode'],used=used)
                assert observation==d['observation']
                used+=observation['extra_cost']
                override=d['selected'] if trace['override_at']==index+1 else None
                assert d==decide(step,observation,alternate=override)
                state=d['selected']['state'] if d['selected'] else None
    assert used==trace['extra_observations'] and used<=MAX_EXTRA
    assert trace['success']==steps[-1]['success'] and not any(s['success'] for s in steps[:-1])
    if state is None:
        assert len(decisions)==len(steps) and not trace['success']
    else:
        assert len(decisions)==len(steps)-1
        assert trace['success'] or len(steps)==MAX_ATTEMPTS[item['mechanism']]


def expected_paths(value,reference,q):
    scene=value['scene']
    item=dict(scene,id=scene['id']+'_qualification',arm='new_rule')
    directory=ROOT/'tasks'/scene['id']
    paths=[]
    for mode in modes(item):
        path=directory/mode/'result.json'
        trace=read(path)
        assert trace['item']==item and trace['mode']==mode and trace['override_at'] is None
        assert trace['attempts'][0]==q['steps'][1]
        audit_trace(trace,reference)
        paths.append(str(path))
        target=branch_target(trace) if item['mechanism']=='side_effect' else None
        if target:
            index,selected=target
            path=directory/'alternate/result.json'
            branch=read(path)
            assert branch['item']==item and branch['mode']==mode and branch['override_at']==index+1
            assert branch['attempts'][:index+1]==trace['attempts'][:index+1]
            assert branch['decisions'][:index]==trace['decisions'][:index]
            assert branch['decisions'][index]['selected']==selected
            audit_trace(branch,reference)
            paths.append(str(path))
    return paths


def audit_scene(value):
    scene=value['scene']
    q=read(ROOT/'qualification'/scene['id']/'result.json')
    qualify_audit(q,scene)
    assert value['status']=='completed' and value['eligible']==q['eligible']
    assert value['model'] is None and not value['test_used'] and not value['training_approved']
    paths={s['result_path'] for s in q['steps']}
    if q['eligible']:
        reference=read(q['steps'][0]['result_path'])['records'][0]
        assert value['trajectories']==expected_paths(value,reference,q)
    else:
        assert not value['trajectories']
    trajectories=[read(p) for p in value['trajectories']]
    for trace in trajectories:
        paths.update(s['result_path'] for s in trace['attempts'])
    disk=set((ROOT/'tasks'/scene['id']).glob('**/attempt_*/result.json'))
    disk.update((ROOT/'qualification'/scene['id']).glob('[01]/result.json'))
    assert {str(p) for p in disk}==paths
    assert len(paths)<=MAX_PHYSICAL[scene['mechanism']]
    return dict(id=scene['id'],mechanism=scene['mechanism'],passed=True,eligible=q['eligible'],
        qualification=q['status'],physical_executions=len(paths),trajectories=len(trajectories),
        extra_observations=sum(t['extra_observations'] for t in trajectories),
        successes={Path(p).parent.name:t['success'] for p,t in zip(value['trajectories'],trajectories)},
        model_calls=0,training_approved=False,test_used=False)
