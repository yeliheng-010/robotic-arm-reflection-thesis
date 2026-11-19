"""同可见反馈、同候选空间；无模型失败后的规则兜底。"""
import json
from copy import deepcopy
from bounded.selection import unique_object
from loopstudy.actions import candidates,choose_rule
from rc_common import MAX_ATTEMPTS
from rc_client import generate

SYSTEM='''你是机械臂错误反馈控制器。只输出严格JSON {"action_id":"展示的合法ID"}。
根据当前失败的阶段、测量、接触对象、已执行历史和剩余预算，从展示的候选中选择下一次修正。
候选由程序生成，不是成功标签；测量残差不保证是当前失败原因，运输阶段IK失败不能仅据抓取残差解释。
最多三次物理执行，每次修正后重置同一布局再执行；历史只属于已执行状态，没有未来结果。
不得生成新参数，不得选择未展示ID。本轮没有OBSERVE，不允许追加观测。单位米。'''


def visible_history(steps,decisions):
    rows=[]
    for i,d in enumerate(decisions):
        if d['selected'] is not None and i+1<len(steps):
            feedback=steps[i+1]['feedback']
            rows.append(dict(action=deepcopy(d['selected']),success=steps[i+1]['success'],
                feedback=deepcopy(feedback)))
    return rows


def messages(step,rows,history):
    body=dict(after_attempt=step['index'],remaining_executions=MAX_ATTEMPTS-step['index'],
        state=step['state'],feedback=step['feedback'],candidates=rows,
        legal_action_ids=[r['id'] for r in rows],history=history)
    return [dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(body,ensure_ascii=False,allow_nan=False))]


def parse(text,rows):
    value=json.loads(text,object_pairs_hook=unique_object)
    if not isinstance(value,dict) or set(value)!={'action_id'}:
        raise ValueError('Expected exactly action_id')
    selected=[r for r in rows if r['id']==value['action_id']]
    if len(selected)!=1:
        raise ValueError('Unavailable action')
    return selected[0]


def decide(steps,decisions,*,method):
    step=steps[-1]
    value=dict(after_attempt=step['index'],before=step['state'],feedback=step['feedback'],
               candidates=[],selected=None)
    if method=='retry':
        value['selected']=dict(id='retry',kind='retry',changes={},state=deepcopy(step['state']))
        return value
    rows=candidates(step['feedback'],step['state'],decisions,legacy=False)
    value['candidates']=rows
    if not rows:
        return dict(value,invalid='Candidate set exhausted')
    if method=='rule':
        value['selected']=choose_rule(rows,step['state'],report=step['feedback'])
        return value
    assert method=='model'
    event=generate(messages(step,rows,visible_history(steps,decisions)))
    value['event']=event
    if event.get('service_failure'):
        return dict(value,service_failure=event['service_failure'])
    try:
        if 'invalid' in event:
            raise ValueError(event['invalid'])
        value['selected']=parse(event['text'],rows)
    except (ValueError,KeyError,TypeError) as error:
        value['invalid']=repr(error)
    return value
