"""从固定来源重新构造每分支；核验原物理判据与相同动作可复现性。"""
from itertools import combinations
from loopstudy import audit as original
from hardstudy.intervention import audit as intervention_audit
from hardstudy.bridge import bound
from od_common import ROOT,SOURCE,read,LEVELS,SELECTORS
from od_source import source_input
from od_branches import branch_input


def same_execution(a,b):
    ignored={'result_path','result_sha256'}
    assert {k:v for k,v in a.items() if k not in ignored}=={k:v for k,v in b.items() if k not in ignored}


def audit_branch(row,case,*,source,reference):
    base=branch_input(case,row['level'],selector=row['selector'])
    assert {k:v for k,v in row.items() if k not in ('step','success','status')}==base
    assert row['status']=='completed'
    if row['selected'] is None:
        assert row['invalid'] and row['step'] is None and not row['success']
        return False
    step=row['step']
    index=source['step']['index']+1
    folder=ROOT/'tasks'/case['case_id']/f"{row['selector']}_l{row['level']}"/f'attempt_{index}'
    assert step['result_path']==str(folder/'result.json') and step['index']==index
    assert step['state']==row['selected']['state'] and row['success']==step['success']
    with bound(source['trace']['item']):
        intervention_audit(step,source['trace']['item'])
        original.physical(step,source['trace']['item'],reference)
    prior=source['trace']['attempts'][case['decision_index']+1]
    matched=prior['state']==step['state']
    if matched:
        same_execution(prior,step)
    return matched


def audit_case(value):
    case=value['case']
    assert value['status']=='completed' and not value['test_used'] and not value['training_approved']
    rows=value['branches']
    assert [(r['level'],r['selector']) for r in rows]==[(n,s) for n in LEVELS for s in SELECTORS]
    source=source_input(case)
    q=read(SOURCE/'qualification'/case['scene_id']/'result.json')
    reference=read(q['steps'][0]['result_path'])['records'][0]
    matched=sum(audit_branch(r,case,source=source,reference=reference) for r in rows)
    for a,b in combinations(rows,2):
        if a['step'] and b['step'] and a['step']['state']==b['step']['state']:
            same_execution(a['step'],b['step'])
    paths={r['step']['result_path'] for r in rows if r['step']}
    disk={str(p) for p in (ROOT/'tasks'/case['case_id']).glob('*/attempt_*/result.json')}
    assert paths==disk and len(paths)<=6
    return dict(case_id=case['case_id'],passed=True,physical_executions=len(paths),branches=len(rows),
        original_action_reproductions=matched,invalid=sum(bool(r['invalid']) for r in rows),
        outcomes=[dict(selector=r['selector'],level=r['level'],success=r['success'],
            attempted=r['step'] is not None,extra_observations=r['extra_observations']) for r in rows])
