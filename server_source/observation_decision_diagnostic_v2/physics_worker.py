"""固定快照选新配置后，以相同场景种子重置重试一次；不冒充动态状态恢复。"""
import argparse
from hardstudy.intervention import attempt
from od_common import ROOT,verify,save,LEVELS,SELECTORS
from od_source import source_input
from od_branches import branch_input


def execute(index):
    case=verify()['cases'][index]
    directory=ROOT/'tasks'/case['case_id']
    directory.mkdir(parents=True,exist_ok=False)
    source=source_input(case)
    rows=[]
    value=dict(case=case,status='running',branches=rows,test_used=False,training_approved=False)
    for level in LEVELS:
        for selector in SELECTORS:
            folder=directory/f'{selector}_l{level}'
            folder.mkdir(exist_ok=False)
            row=branch_input(case,level,selector=selector)
            save(folder/'input.json',row)
            step=None
            if row['selected'] is not None:
                n=source['step']['index']+1
                step=attempt(source['trace']['item'],row['selected']['state'],directory=folder/f'attempt_{n}',index=n)
            row.update(step=step,success=bool(step and step['success']),status='completed')
            save(folder/'result.json',row)
            rows.append(row)
            save(directory/'progress.json',value)
    value['status']='completed'
    save(directory/'result.json',value)
    from od_physics_audit import audit_case
    save(directory/'summary.json',audit_case(value))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('index',type=int)
    execute(parser.parse_args().index)
