"""无模型、无反馈失真的控制先行资格检查。"""
import json
from pathlib import Path
import numpy as np
from loopstudy.episode import attempt
from loopstudy.actions import initial
from loopstudy.audit import physical
from stability.collection_status import atomic
from expand.design import ROOT
from expand.bridge import bound,geometry

ELIGIBLE=('challenge','easy_control')


def classify(geometry_ok,control,*,success,contact):
    if not geometry_ok:
        return 'geometry_ineligible'
    if not control:
        return 'control_failed'
    if success:
        return 'easy_control'
    return 'challenge' if contact else 'non_target_failure'


def record(step):
    return json.loads(Path(step['result_path']).read_text())['records'][0]


def contact(step):
    error=record(step).get('error') or {}
    return error.get('error_type')=='collision' and any(
        'SafetyDivider' in pair for pair in error.get('evidence',{}).get('contacts',[]))


def run(item):
    directory=ROOT/'qualification'/item['id']
    directory.mkdir(parents=True,exist_ok=False)
    checked=geometry(item)
    row=dict(item=item,geometry=checked,steps=[],status='geometry_ineligible',eligible=False)
    if checked['passed']:
        for enabled in (False,True):
            with bound(item,enabled=enabled):
                step=attempt(item,initial(),directory=directory/str(int(enabled)),index=1)
            row['steps'].append(step)
            atomic(directory/'progress.json',row)
            if not step['success'] and not enabled:
                break
        control=row['steps'][0]['success']
        treatment=row['steps'][-1] if control else None
        row['status']=classify(True,control,success=bool(treatment and treatment['success']),
                               contact=bool(treatment and contact(treatment)))
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
        for step in steps:
            assert step['index']==1 and step['state']==initial()
            physical(step,item,reference)
    treatment=steps[1] if len(steps)==2 else None
    expected=classify(True,steps[0]['success'],success=bool(treatment and treatment['success']),
                      contact=bool(treatment and contact(treatment)))
    assert value['status']==expected and value['eligible']==(expected in ELIGIBLE)
