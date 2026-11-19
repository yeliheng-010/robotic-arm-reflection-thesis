"""真实冒烟记录的物理、模型身份、投影和预算篡改必须被拒绝。"""
import copy
from common import ROOT,read,save
from audit_task import audit


def reject(value,entry):
    try:
        audit(value,entry)
    except (AssertionError,ValueError,KeyError):
        return
    raise AssertionError('Tampered diagnostic accepted')


def run(entries):
    checks=[]
    for variant in ('budget4','no_missing'):
        for method in ('base','previous159','new189'):
            entry=next(e for e in entries if e['variant']==variant and e['method']==method)
            original=read(ROOT/'tasks'/entry['uid']/'result.json')
            assert original['decisions'], 'No real model decision in smoke'
            audit(original,entry)
            value=copy.deepcopy(original)
            value['attempts'][0]['result_sha256']='0'*64
            reject(value,entry)
            value=copy.deepcopy(original)
            value['decisions'][0]['event']['request']['model']='other'
            reject(value,entry)
            value=copy.deepcopy(original)
            value['attempts'][0]['noise_audit']['grasp_residual_xy']['delta'][0]+=1
            reject(value,entry)
            bad_entry=dict(entry,max_attempts=3 if variant=='budget4' else 4)
            reject(original,bad_entry)
            checks.append(dict(variant=variant,method=method,rejections=4))
    save(ROOT/'tamper_checks.json',dict(passed=True,checks=checks,total_rejections=24))
