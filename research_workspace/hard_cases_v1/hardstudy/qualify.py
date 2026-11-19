"""先确认无干预控制成功，保留所有机制的实际故障分布。"""
import json
from pathlib import Path
from loopstudy.actions import initial
from loopstudy.audit import physical
from stability.collection_status import atomic
from hardstudy.design import ROOT
from hardstudy.bridge import bound,geometry
from hardstudy.intervention import attempt,audit as audit_intervention

ELIGIBLE=('challenge','easy_control')


def classify(geometry_ok,control,*,success):
    if not geometry_ok:
        return 'geometry_ineligible'
    if not control:
        return 'control_failed'
    return 'easy_control' if success else 'challenge'


def record(step):
    return json.loads(Path(step['result_path']).read_text())['records'][0]


def run(item):
    directory=ROOT/'qualification'/item['id']
    directory.mkdir(parents=True,exist_ok=False)
    checked=geometry(item)
    row=dict(item=item,geometry=checked,steps=[],status='geometry_ineligible',eligible=False)
    if checked['passed']:
        for enabled in (False,True):
            step=attempt(item,initial(),directory=directory/str(int(enabled)),index=1,enabled=enabled)
            row['steps'].append(step)
            atomic(directory/'progress.json',row)
            if not enabled and not step['success']:
                break
        row['status']=classify(True,row['steps'][0]['success'],success=row['steps'][-1]['success'])
        row['eligible']=row['status'] in ELIGIBLE
    atomic(directory/'result.json',row)
    audit(row,item)
    atomic(directory/'summary.json',dict(id=item['id'],status=row['status'],eligible=row['eligible'],
        executed=len(row['steps']),passed=True,model_calls=0,training_approved=0))
    return row


def audit(value,item):
    assert value['item']==item and value['geometry']==geometry(item)
    steps=value['steps']
    if not value['geometry']['passed']:
        assert not steps and value['status']=='geometry_ineligible' and not value['eligible']
        return
    assert len(steps)==(2 if steps[0]['success'] else 1)
    reference=record(steps[0])
    with bound(item):
        for index,step in enumerate(steps):
            assert step['index']==1 and step['state']==initial()
            audit_intervention(step,item,enabled=bool(index))
            physical(step,item,reference)
    expected=classify(True,steps[0]['success'],success=steps[-1]['success'])
    assert value['status']==expected and value['eligible']==(expected in ELIGIBLE)
