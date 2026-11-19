"""在真实冒烟记录副本上检查篡改会被审计拒绝。"""
import copy
from common import ROOT,read,save
from audit_task import audit


def must_reject(value,entry):
    try:
        audit(value,entry)
    except (AssertionError,ValueError,KeyError):
        return
    raise AssertionError('Tampered record passed audit')


def run(entries):
    checked=[]
    for method in ('base','previous159','new189'):
        found=None
        for entry in entries:
            if entry['method']!=method or not entry['eligible']:
                continue
            value=read(ROOT/'tasks'/entry['uid']/'result.json')
            if value['decisions'] and 'response' in value['decisions'][0].get('event',{}):
                found=(entry,value)
                break
        assert found,'Smoke must include actual model decisions'
        entry,original=found
        audit(original,entry)
        value=copy.deepcopy(original)
        value['attempts'][0]['result_sha256']='0'*64
        must_reject(value,entry)
        value=copy.deepcopy(original)
        value['decisions'][0]['event']['request']['model']='other-model'
        must_reject(value,entry)
        value=copy.deepcopy(original)
        value['decisions'][0]['feedback']['unexpected_truth']=1
        must_reject(value,entry)
        value=copy.deepcopy(original)
        value['decisions'][0]['event']['response']['identity']={'tampered':True}
        must_reject(value,entry)
        checked.append(dict(method=method,uid=entry['uid'],rejections=4))
    save(ROOT/'tamper_checks.json',dict(passed=True,checks=checked,total_rejections=12))
