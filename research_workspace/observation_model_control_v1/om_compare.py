"""路径/文件hash之外严格复现旧规则；同状态同聚合菜单一致。"""
from itertools import combinations
from om_common import SOURCE,read

PATH_FIELDS={'result_path','result_sha256','source_sha256'}


def semantic(value):
    if isinstance(value,dict):
        return {k:semantic(v) for k,v in value.items() if k not in PATH_FIELDS}
    if isinstance(value,list):
        return [semantic(v) for v in value]
    return value


def old_rule(scene,method,trace):
    old=read(SOURCE/'tasks'/scene['id']/method.split('_')[1]/'result.json')
    assert semantic(trace['attempts'])==semantic(old['attempts']),'Rule physics changed: '+scene['id']
    assert trace['success']==old['success'] and trace['extra_observations']==old['extra_observations']
    fields=('after_attempt','before','feedback','candidates','selected','observation')
    assert len(trace['decisions'])==len(old['decisions'])
    for a,b in zip(trace['decisions'],old['decisions']):
        assert all(semantic(a[k])==semantic(b[k]) for k in fields),'Rule decision changed: '+scene['id']


def compare_scene(scene,q,traces):
    prior=read(SOURCE/'qualification'/scene['id']/'result.json')
    assert q['eligible']==prior['eligible'] and q['status']==prior['status']
    assert semantic(q['steps'])==semantic(prior['steps'])
    checks=dict(old_rule_trajectories=0,matched_states=0,matched_menus=0)
    for method,t in traces.items():
        if method.startswith('rule_'):
            old_rule(scene,method,t)
            checks['old_rule_trajectories']+=1
    for (ma,a),(mb,b) in combinations(traces.items(),2):
        for i,(sa,sb) in enumerate(zip(a['attempts'],b['attempts'])):
            if sa['state']!=sb['state']:
                continue
            assert semantic(sa)==semantic(sb)
            checks['matched_states']+=1
            if i>=min(len(a['decisions']),len(b['decisions'])):
                continue
            da,db=a['decisions'][i],b['decisions'][i]
            assert semantic(da['observation']['samples'])==semantic(db['observation']['samples'])
            if ma.split('_')[1]==mb.split('_')[1]:
                assert da['feedback']==db['feedback'] and da['candidates']==db['candidates']
                checks['matched_menus']+=1
    return checks
