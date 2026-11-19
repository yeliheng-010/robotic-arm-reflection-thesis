"""私有资格判断只用于数据审计，不注入模型输入。"""
import hashlib
import json

NATURAL_ERRORS={'empty_grasp','object_dropped','placement_offset','collision','no_grasp_candidate'}


def eligible(record):
    error=record.get('error') or {}
    evidence=error.get('evidence',{})
    if evidence.get('route_planning_rejected') or evidence.get('guard_kind')=='path_admissibility':
        return False,'planning_rejection'
    kind=error.get('error_type')
    if kind not in NATURAL_ERRORS:
        return False,'unqualified_error_type:'+str(kind)
    return True,'natural_execution_or_perception_failure'


def action(name):
    if name=='LOWER_10MM':
        return dict(id='SET_GRASP_OFFSET',args=dict(delta_m=[0.,0.,-.01]))
    if name=='SLOW_3X':
        return dict(id='SET_TIME_SCALE',args=dict(value=3.))
    raise ValueError('Unknown executed action')


def snapshot(item,summary):
    private=summary['private'][0]
    value=dict(task={k:item[k] for k in ('source','destination')},
               state=private['state_sha256'],clean=private['clean_sha256'])
    raw=json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':'))
    return hashlib.sha256(raw.encode()).hexdigest()
