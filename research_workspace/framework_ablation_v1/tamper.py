"""真实冒烟副本必须拒绝物理、候选、策略和模型身份篡改。"""
from copy import deepcopy
from common import ROOT,METHODS,read,save
from audit_task import audit


def must_reject(value,entry):
    try:
        audit(value,entry)
    except (AssertionError,ValueError,KeyError):
        return
    raise AssertionError('Tampered record passed audit')


def run(entries):
    checks=[]
    for method in METHODS:
        found=[]
        for entry in entries:
            if entry['method']==method and entry['eligible']:
                value=read(ROOT/'tasks'/entry['uid']/'result.json')
                if value['decisions']:
                    found.append((entry,value))
        assert found,'Smoke requires actual decisions for '+method
        entry,original=found[0]
        mutations=[lambda v:v['attempts'][0].update(result_sha256='0'*64),
                   lambda v:v['decisions'][0]['feedback'].update(unexpected_truth=1),
                   lambda v:v['decisions'][0]['selected'].update(id='forged'),
                   lambda v:v['decisions'][0].update(source='forged')]
        if method in ('current','history'):
            mutations += [lambda v:v['decisions'][0]['event']['request'].update(model='other'),
                          lambda v:v['decisions'][0]['event']['response'].update(active_adapter_sha256='forged')]
        for mutate in mutations:
            value=deepcopy(original)
            mutate(value)
            must_reject(value,entry)
        checks.append(dict(method=method,uid=entry['uid'],rejections=len(mutations)))
    output=dict(passed=True,checks=checks,total_rejections=sum(c['rejections'] for c in checks))
    save(ROOT/'tamper_checks.json',output)
    return output
