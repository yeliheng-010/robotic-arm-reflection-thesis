"""任务记录保留显式跳过；执行样本与计划分母分开。"""
import json
from stability.collection_status import atomic
from hardstudy.design import ROOT
from hardstudy.qualify import audit as audit_qualification
from hardstudy.episode import run
from hardstudy.audit import audit


def qualification(item):
    scene={k:v for k,v in item.items() if k!='arm'}
    scene['id']=item['scene_id']
    value=json.loads((ROOT/'qualification'/scene['id']/'result.json').read_text())
    audit_qualification(value,scene)
    return value


def execute(item):
    qualified=qualification(item)
    directory=ROOT/'tasks'/item['id']
    base={k:item[k] for k in ('id','scene_id','pair_id','source','destination','seed','factor',
                              'arm','split','noise_index','noise_profile')}
    base['qualification_status']=qualified['status']
    if not qualified['eligible']:
        directory.mkdir(parents=True,exist_ok=False)
        row=dict(base,status='not_run_ineligible',executed=False,success=None,attempts=0,
                 calls=0,invalid=0,service_errors=0,noise_projections=0)
    else:
        result=run(item,directory)
        checked=audit(result,item)
        row=dict(base,status=result['status'],executed=True,success=result['success'],audit=checked,
                 **{k:v for k,v in checked.items() if k!='passed'})
    row.update(training_approved=0,test_used=False)
    atomic(directory/'summary.json',row)
    return row


def read(item):
    directory=ROOT/'tasks'/item['id']
    row=json.loads((directory/'summary.json').read_text())
    qualified=qualification(item)
    for key in ('id','scene_id','pair_id','source','destination','seed','factor','arm','split','noise_index','noise_profile'):
        assert row[key]==item[key]
    assert row['qualification_status']==qualified['status']
    assert row['executed']==qualified['eligible'] and row['training_approved']==0 and not row['test_used']
    result=None
    if row['executed']:
        result=json.loads((directory/'result.json').read_text())
        checked=audit(result,item)
        assert row['audit']==checked and row['status']==result['status'] and row['success']==result['success']
        assert all(row[k]==v for k,v in checked.items() if k!='passed')
    else:
        assert row['status']=='not_run_ineligible' and row['success'] is None
        assert all(row[k]==0 for k in ('attempts','calls','invalid','service_errors','noise_projections'))
        assert not (directory/'result.json').exists()
    return row,result
