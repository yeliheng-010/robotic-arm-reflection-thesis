"""原始物理记录与预算/测量篡改拒绝，使用真实已执行分支。"""
from copy import deepcopy
from od_physics_audit import audit_case
from od_common import SELECTORS


def check(values):
    rejected=[]
    for selector in SELECTORS:
        value=next(v for v in values if any(r['selector']==selector and r['step'] for r in v['branches']))
        index=next(i for i,r in enumerate(value['branches']) if r['selector']==selector and r['step'])
        mutations={'physical_hash':lambda r:r['step'].update(result_sha256='0'*64),
            'source':lambda r:r.update(source_sha256='0'*64),
            'budget':lambda r:r.update(extra_observations=99),
            'measurement':lambda r:r['samples'][0].update(audit={'forged':True}),
            'selection':lambda r:r['selected'].update(id='forged'),
            'success':lambda r:r.update(success=not r['success'])}
        for name,mutate in mutations.items():
            changed=deepcopy(value)
            mutate(changed['branches'][index])
            assert changed!=value
            try:
                audit_case(changed)
            except (AssertionError,ValueError,KeyError):
                rejected.append(dict(selector=selector,kind=name))
            else:
                raise AssertionError('Accepted physics tamper: '+name)
    assert len(rejected)==12
    return rejected
