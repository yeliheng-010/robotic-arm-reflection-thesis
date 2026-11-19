"""四种方法真实记录篡改覆盖，模型另外检查adapter身份。"""
from copy import deepcopy
from om_common import ROOT,read,METHODS
from om_audit import audit_trace


def probes(values):
    found={}
    for value in values:
        for path in value['trajectories']:
            t=read(path)
            if t['decisions'] and t['method'] not in found:
                q=read(ROOT/'qualification'/value['scene']['id']/'result.json')
                found[t['method']]=(t,read(q['steps'][0]['result_path'])['records'][0])
    assert set(found)==set(METHODS),'Missing real decisions for tamper checks'
    return found


def check(values):
    rejections=[]
    for method,(original,reference) in probes(values).items():
        mutations={'physical_hash':lambda t:t['attempts'][0].update(result_sha256='0'*64),
            'observation_state':lambda t:t['decisions'][0]['observation']['samples'][0].update(state={}),
            'visible_truth':lambda t:t['decisions'][0]['feedback']['evidence'].update(hidden_truth=1),
            'budget':lambda t:t.update(extra_observations=99),
            'success':lambda t:t.update(success=not t['success'])}
        if method.startswith('base_'):
            mutations['adapter_identity']=lambda t:t['decisions'][0]['event']['response'].update(active_adapter_sha256='forged')
        for name,mutate in mutations.items():
            changed=deepcopy(original)
            mutate(changed)
            try:
                audit_trace(changed,reference)
            except (AssertionError,ValueError,KeyError):
                rejections.append(dict(method=method,kind=name))
            else:
                raise AssertionError('Tamper accepted: '+method+' '+name)
    assert len(rejections)==22
    return dict(passed=True,count=len(rejections),rejections=rejections)
