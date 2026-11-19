from reflection.__main__ import bootstrap
bootstrap()
import argparse
from pathlib import Path
from qp_common import ROOT,read,save,sha,verify,change,ACTIONS
from nc_audit_attempt import audit as attempt
from nc_audit_frames import view
from rb_audit import route
from cp_audit import candidate_audit
from rv_runtime import mode
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from sr_audit import measured


def inspect(case):
    folder=ROOT/'cases'/case['item']['id']
    result=read(folder/'result.json')
    assert result['status']=='completed' and result['manifest_sha256']==sha(ROOT/'manifest.json')
    assert result['model_calls']==0
    steps=result['steps']
    assert 1<=len(steps)<=3 and len(result['actions'])==len(steps)-1
    assert len(result['observations'])==len(steps)
    state,control,rows=case['state'],dict(grasp_mode='world_down'),[]
    for index,step in enumerate(steps,1):
        assert step['index']==index and step['state']==state and step['control']==control
        with self_context(),joint_context(case['config']),mode(control):
            record,_,_=attempt(case,step)
            checked=route(case,step,record)
        summary=view(result['observations'][index-1],case)
        assert len(summary['paths'])==1 and summary['remaining']==0
        candidate_audit(step,case['config'])
        evidence=measured(Path(step['session_path']))
        save(Path(step['session_path'])/'contact_summary.json',evidence)
        rejected=(record.get('error') or {}).get('evidence',{}).get('route_planning_rejected',False)
        rows.append(dict(index=index,success=step['success'],route=checked,planning_rejected=rejected,
            contacts={k:v for k,v in evidence.items() if k!='closing_end'}))
        if index<len(steps):
            assert not step['success'] and result['actions'][index-1]==dict(after_attempt=index,action=ACTIONS[index-1])
            state,control=change(state,control,action=ACTIONS[index-1])
    assert result['success']==steps[-1]['success']
    return dict(id=case['item']['id'],attempts=len(steps),success=result['success'],rows=rows)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--case-id',required=True)
    name=parser.parse_args().case_id
    case=next(c for c in verify()['cases'] if c['item']['id']==name)
    row=inspect(case)
    files=[p for p in (ROOT/'cases'/name).rglob('*') if p.is_file()]
    save(ROOT/'audits'/(name+'.json'),dict(passed=True,row=row,training_ready=False,
        identities={str(p):sha(p) for p in files},manifest_sha256=sha(ROOT/'manifest.json')))
    print(dict(id=name,attempts=row['attempts'],success=row['success']),flush=True)


if __name__=='__main__':
    main()
