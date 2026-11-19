"""只改动作表示或明确指令；费用理解与执行阶段分开诊断。"""
import json
from copy import deepcopy
from bounded.selection import unique_object
from am_policy import SYSTEM

VARIANTS=('baseline','unified_first','unified_last','missing_directive')
DIRECTIVE='\n本变体明确加入专家指令：若quality中任一字段status为missing且remaining_observations>0，先选择OBSERVE；否则自主选择。这是指令遵循诊断。'
PROBE='''仅根据给定上下文回答OBSERVE的权限和费用，不选择动作。
OBSERVE每次消耗1次额外观测、0次物理执行；是否合法以legal_action_ids为准。
只输出JSON，字段严格为observe_legal（布尔）、observation_cost（整数）、physical_cost（整数）、remaining_observations（整数）。'''
EXECUTE_ONLY='\n本次是固定观测数诊断：观测阶段已经结束，本次只能选执行候选，不可继续补看。remaining_observations保留真实余量，不表示预算已经耗尽。'


def eligible(body):
    return body['remaining_observations']>0 and any(q['status']=='missing' for q in body['quality'].values())


def variant(original,name):
    assert name in VARIANTS or name=='comprehension'
    result=deepcopy(original)
    if name=='baseline':
        return result
    body=json.loads(result[1]['content'])
    if name in ('unified_first','unified_last','missing_directive') and 'OBSERVE' in body['legal_action_ids']:
        entry=dict(id='OBSERVE',kind='observation',explanation='对同一失败状态补看一次，可能仍缺测或离群，不执行物理修正。',
            facts=dict(extra_observation_cost=1,physical_execution_cost=0,changes_executor_state=False))
        body['candidates']=body['candidates']+[entry] if name=='unified_last' else [entry]+body['candidates']
    if name=='missing_directive':
        result[0]['content']+=DIRECTIVE
    if name=='comprehension':
        result[0]['content']=PROBE
    result[1]['content']=json.dumps(body,ensure_ascii=False,allow_nan=False)
    return result


def probe_expected(body):
    return dict(observe_legal='OBSERVE' in body['legal_action_ids'],observation_cost=1,
        physical_cost=0,remaining_observations=body['remaining_observations'])


def parse_probe(text):
    value=json.loads(text,object_pairs_hook=unique_object)
    keys={'observe_legal','observation_cost','physical_cost','remaining_observations'}
    if not isinstance(value,dict) or set(value)!=keys or type(value['observe_legal']) is not bool:
        raise ValueError('Probe schema mismatch')
    if any(type(value[k]) is not int for k in keys-{'observe_legal'}):
        raise ValueError('Probe requires integer costs')
    return value


def execution_prompt(value):
    body=deepcopy(value)
    body.update(history=[],observation_phase_closed=True)
    body['legal_action_ids']=[r['id'] for r in body['candidates']]
    return [dict(role='system',content=SYSTEM+EXECUTE_ONLY),
            dict(role='user',content=json.dumps(body,ensure_ascii=False,allow_nan=False))]
