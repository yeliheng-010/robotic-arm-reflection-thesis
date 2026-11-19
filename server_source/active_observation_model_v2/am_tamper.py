"""基于真实轨迹验证预算、历史、请求及物理记录不能篡改。"""
from copy import deepcopy
from am_common import ROOT,read,METHODS,MODEL_METHODS
from am_audit import audit_trace


def check(values):
    found={}
    for v in values:
        for path in v['trajectories']:
            t=read(path)
            if t['decisions'] and t['method'] not in found:
                q=read(ROOT/'qualification'/v['scene']['id']/'result.json')
                found[t['method']]=(t,read(q['steps'][0]['result_path'])['records'][0])
    assert set(found)==set(METHODS),'No auditable decisions for a method'
    rejected=[]
    for method,(original,reference) in found.items():
        mutations={'physical_hash':lambda t:t['attempts'][0].update(result_sha256='0'*64),
            'budget':lambda t:t.update(extra_observations=99),
            'success':lambda t:t.update(success=not t['success']),
            'truth':lambda t:t['decisions'][0]['choices'][0]['context'].update(hidden_truth=1),
            'allocation':lambda t:t['decisions'][0]['choices'][0].update(action='FORGED'),
            'state':lambda t:t['decisions'][0]['observation']['samples'][0].update(state={})}
        if method in MODEL_METHODS:
            mutations['prompt_history']=lambda t:t['decisions'][0]['choices'][0]['event']['request']['messages'][1].update(content='{"history":["forged"]}')
            mutations['model_identity']=lambda t:t['decisions'][0]['choices'][0]['event']['response']['identity'].update(adapter_enabled=True)
        for name,mutate in mutations.items():
            changed=deepcopy(original)
            mutate(changed)
            assert changed!=original
            try:
                audit_trace(changed,reference)
            except (AssertionError,ValueError,KeyError,StopIteration):
                rejected.append(dict(method=method,kind=name))
            else:
                raise AssertionError('Tamper accepted: '+name)
    assert len(rejected)==28
    return dict(passed=True,count=len(rejected),rejections=rejected)
