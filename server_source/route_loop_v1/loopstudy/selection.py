"""严格的候选ID选择；不代选、不修补非法模型响应。"""
import json
from bounded.selection import unique_object
from flashnext.client import generate
from loopstudy.actions import choose_rule,PROFILES

SYSTEM = '''你是机械臂搬运任务的有限候选选择器，只能选择展示的一个候选。
候选和解释来自外部规则，不代表已经成功；新配置的动作语义由执行器提供。
motion_context区分carry_transport（携物运输）与place_descent（运输后放置下降）。
contact_details中的body是实际接触部位，root只是归类节点。
结合当前阶段、接触证据、当前参数/配置与过去失败动作，选择最相关的修正。
运输失败可以考虑抬升；若已通过运输但在下降碰撞，需考虑下降路径/姿态，不要把它当作抓取前接近。
profile配置控制下降姿态，parameters控制原参数，两者都参与实际执行。
只输出严格JSON {"action_id":"一个展示的候选ID"}，不得添加字段或解释。'''
MAX_TOKENS = 128


def resolve(text,rows):
    value = json.loads(text,object_pairs_hook=unique_object)
    if not isinstance(value,dict) or set(value)!={'action_id'} or not isinstance(value['action_id'],str):
        raise ValueError('Expected exactly one string action_id')
    matched = [r for r in rows if r['id']==value['action_id']]
    if len(matched)!=1:
        raise ValueError('Unknown or ambiguous action_id')
    return matched[0]


def messages(report,state,*,rows,history):
    past = [dict(error=h['feedback'],before=h['before'],selected=h['selected']) for h in history]
    value = dict(error=report,state=state,candidates=rows,history=past,
                 executor_profiles={k:dict(yaw_deg=v,timing='descent') for k,v in PROFILES.items()})
    return [dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(value,ensure_ascii=False))]


def select(arm,decision,history):
    report,state,rows = decision['feedback'],decision['before'],decision['candidates']
    if arm!='hybrid':
        return dict(selected=choose_rule(rows,state,report=report,legacy=arm=='old_rule'),model=None,
                    source='deterministic_stage_rule')
    event = generate(messages(report,state,rows=rows,history=history),max_tokens=MAX_TOKENS)
    try:
        if 'error' in event:
            raise ValueError(event['error'])
        selected = resolve(event['text'],rows)
        return dict(selected=selected,event=event,source='hybrid_model_selection_rule_candidates')
    except (ValueError,KeyError,TypeError) as error:
        return dict(selected=None,event=event,invalid=repr(error),
                    source='hybrid_model_selection_rule_candidates')
