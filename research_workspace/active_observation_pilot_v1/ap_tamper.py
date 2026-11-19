"""实际记录的预算/策略/真值/物理篡改必须拒绝。"""
from copy import deepcopy
from ap_common import ROOT,read,METHODS
from ap_audit import audit_trace


def check(values):
    found={}
    for value in values:
        for path in value['trajectories']:
            t=read(path)
            if t['decisions'] and t['method'] not in found:
                q=read(ROOT/'qualification'/value['scene']['id']/'result.json')
                found[t['method']]=(t,read(q['steps'][0]['result_path'])['records'][0])
    assert set(found)==set(METHODS),'Smoke has no auditable decisions for every policy'
    rejected=[]
    for method,(original,reference) in found.items():
        mutations={'physical_hash':lambda t:t['attempts'][0].update(result_sha256='0'*64),
            'state':lambda t:t['decisions'][0]['observation']['samples'][0].update(state={}),
            'truth':lambda t:t['decisions'][0]['feedback']['evidence'].update(hidden_truth=1),
            'budget':lambda t:t.update(extra_observations=99),
            'allocation':lambda t:t['decisions'][0]['observation'].update(events=[{'forged':True}]),
            'success':lambda t:t.update(success=not t['success'])}
        for name,mutate in mutations.items():
            changed=deepcopy(original)
            mutate(changed)
            assert changed!=original,'Tamper requires effective change'
            try:
                audit_trace(changed,reference)
            except (AssertionError,ValueError,KeyError):
                rejected.append(dict(method=method,kind=name))
            else:
                raise AssertionError('Tamper accepted: '+name)
    assert len(rejected)==12
    return dict(passed=True,count=len(rejected),rejections=rejected)
