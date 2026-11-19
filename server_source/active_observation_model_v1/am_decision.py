"""有限观测状态机；模型输出无规则兜底，全部事件可重建。"""
from am_common import MODEL_METHODS,MAX_EXTRA
from ap_sensor import sample,aggregate
from ap_policy import quality
from am_policy import context,messages,parse,rule_action,OBSERVE
from am_client import generate


def choose(value,*,method,history):
    if method not in MODEL_METHODS:
        return dict(action=rule_action(value,method=method))
    if not value['legal_action_ids']:
        return dict(action=None,invalid='No legal action')
    event=generate(messages(value,method=method,history=history))
    if 'service_failure' in event:
        return dict(action=None,event=event,service_failure=event['service_failure'])
    try:
        if 'invalid' in event:
            raise ValueError(event['invalid'])
        return dict(action=parse(event['text'],value),event=event)
    except (ValueError,KeyError,TypeError) as error:
        return dict(action=None,event=event,invalid=repr(error))


def decide(step,item,*,method,used,history):
    samples=[sample(step,item,number=0)]
    choices=[]
    original_used=used
    for _ in range(MAX_EXTRA+1):
        value=context(step,samples,used=used)
        choice=dict(context=value,**choose(value,method=method,history=history))
        choices.append(choice)
        if choice['action']!=OBSERVE:
            break
        used+=1
        samples.append(sample(step,item,number=len(samples)))
    assert choices[-1]['action']!=OBSERVE
    last=choices[-1]
    selected=next((r for r in last['context']['candidates'] if r['id']==last['action']),None)
    observation=dict(samples=samples,extra_cost=used-original_used,
        initial_quality=quality(samples[:1]),final_quality=quality(samples),feedback=aggregate(samples,mode='median'))
    return dict(after_attempt=step['index'],before=step['state'],method=method,choices=choices,
        observation=observation,selected=selected,invalid=last.get('invalid'),service_failure=last.get('service_failure'))
