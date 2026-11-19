"""模型只返回编号；严格解析且无代选，说明来源始终显式。"""
import json
import time
from flashnext.client import request, check_response, MODEL

SOURCE = 'hybrid_llm_selection_rule_candidates_template'
SYSTEM = '''你是机械臂失败修正候选选择器。候选由外部规则生成，不代表已经验证有效。
根据展示的反馈、当前参数与历史选择一个候选。优先选择与实际失败相关的实测偏移补偿。
当前偏移和新偏移是绝对值。缺失测量不能当作零；没有有效测量时进行有限探索。
以motion_segment定位具体阶段，若无此字段再使用failure_stage。抓取前失败不通过抓取后的抬升解决。
抓取候选已变化但仍空抓/掉落时，可以尝试局部抓取深度变化；不要重复历史中失败的相同动作。
只返回JSON {"action_id":"候选编号"}，不输出新参数、解释或额外字段。'''


def unique_object(pairs):
    result = {}
    for key,value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def resolve(text, rows):
    value = json.loads(text,object_pairs_hook=unique_object)
    if not isinstance(value,dict) or set(value)!={'action_id'} or not isinstance(value['action_id'],str):
        raise ValueError('Expected exactly one action_id')
    matched = [r for r in rows if r['id']==value['action_id']]
    if len(matched)!=1:
        raise ValueError('Unknown or ambiguous action_id; no fallback')
    row = matched[0]
    return dict(cause=row['explanation'],changes=row['changes'],source=SOURCE)


def payload(report, values, *, rows, history):
    data = dict(error=report,parameters=values,history=history,candidates=rows)
    schema = dict(type='object',properties={'action_id':{'type':'string','enum':[r['id'] for r in rows]}},
                  required=['action_id'],additionalProperties=False)
    return dict(model=MODEL,temperature=0,seed=42,max_tokens=128,
                chat_template_kwargs={'enable_thinking':False},
                messages=[{'role':'system','content':SYSTEM},
                          {'role':'user','content':json.dumps(data,ensure_ascii=False)}],
                response_format={'type':'json_schema','json_schema':{
                    'name':'candidate_selection','strict':True,'schema':schema}})


def generate(report, values, *, rows, history):
    if not rows:
        raise ValueError('No candidate remaining')
    body = payload(report,values,rows=rows,history=history)
    event = dict(request=body,started_at=time.time(),schema_is_hard_constraint=False)
    try:
        event['response'] = request('/chat/completions',body)
        event['text'] = check_response(event['response'])
        event['parsed'] = resolve(event['text'],rows)
    except Exception as error:
        event.update(error=repr(error),service_error='response' not in event)
    event['elapsed_s'] = time.time()-event['started_at']
    return event
