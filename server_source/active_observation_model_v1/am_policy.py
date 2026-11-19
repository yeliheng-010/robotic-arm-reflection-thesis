"""模型逐次选择补看或候选执行；审计字段不进入可见上下文。"""
import json
from copy import deepcopy
from bounded.selection import unique_object
from loopstudy.actions import candidates,choose_rule,PROFILES
from ap_policy import quality
from ap_sensor import aggregate
from am_common import METHODS,MAX_EXTRA,MAX_ATTEMPTS

OBSERVE='OBSERVE'
SYSTEM='''你是机械臂错误反馈控制器。只输出严格JSON {"action_id":"展示的合法ID"}。
任务是用有限物理尝试完成搬运，同时合理使用有限补看预算。OBSERVE是额外观测同一失败状态，
消耗1次额外观测，不消耗物理尝试；它可能仍缺失或含离群值。没有OBSERVE选项时不可选择它。
其余候选执行修正、消耗1次物理尝试，结果不保证成功。候选由外部规则生成，不是成功标签。
所有残差单位米；默认观测免费，额外观测预算跨状态共用。当前窗口只含当前状态的实际观测，
聚合为逐坐标中位数；一致性启发式不是正确概率，两个一致离群值仍可能错误。
结合可见缺测/冲突、剩余预算、当前失败阶段决定继续补看还是执行候选。
history若存在，只包含此前执行修正和可见结果；空history不代表此前没有执行。
历史属于旧状态，不能当作当前残差。候选profile只控制下降姿态。不得添加解释或其他字段。'''


def context(step,samples,*,used):
    assert 0<=used<=MAX_EXTRA and 1<=step['index']<MAX_ATTEMPTS
    assert all(s['state']==step['state'] and s['source_sha256']==step['result_sha256'] for s in samples)
    feedback=aggregate(samples,mode='median')
    rows=candidates(feedback,step['state'],[],legacy=False)
    return dict(after_attempt=step['index'],state=deepcopy(step['state']),feedback=feedback,
        window=[dict(number=s['number'],feedback=deepcopy(s['feedback'])) for s in samples],
        quality=quality(samples),remaining_observations=MAX_EXTRA-used,
        remaining_executions=MAX_ATTEMPTS-step['index'],candidates=rows,
        legal_action_ids=([OBSERVE] if used<MAX_EXTRA else [])+[r['id'] for r in rows],
        executor_profiles={k:dict(yaw_deg=v,timing='descent') for k,v in PROFILES.items()})


def messages(value,*,method,history):
    assert method in METHODS[2:]
    body=dict(value,history=deepcopy(history) if method=='base_history' else [])
    return [dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(body,ensure_ascii=False,allow_nan=False))]


def parse(text,value):
    result=json.loads(text,object_pairs_hook=unique_object)
    if not isinstance(result,dict) or set(result)!={'action_id'}:
        raise ValueError('Expected exactly action_id')
    action=result['action_id']
    if not isinstance(action,str) or value['legal_action_ids'].count(action)!=1:
        raise ValueError('Unknown or unavailable action')
    return action


def rule_action(value,*,method):
    assert method in METHODS[:2]
    uncertain=any(v['status']!='consistent' for v in value['quality'].values())
    request=value['after_attempt']==1 if method=='fixed_first' else uncertain
    if request and OBSERVE in value['legal_action_ids']:
        return OBSERVE
    rows=value['candidates']
    return choose_rule(rows,value['state'],report=value['feedback'])['id'] if rows else None


def history_entry(value,selected,step):
    phase=step['feedback']['evidence'].get('motion_context',{}).get('phase')
    action={k:deepcopy(selected[k]) for k in ('id','kind','changes','state') if k in selected}
    return dict(after_attempt=value['after_attempt'],before=value['state'],
        action=action,result=dict(attempt=step['index'],success=step['success'],
        error_type=step['feedback']['error_type'],phase=phase),
        state_scope='previous_execution_only_no_residual_reuse')
