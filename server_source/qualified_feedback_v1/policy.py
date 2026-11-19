from copy import deepcopy
import json


def entry(action):
    return dict(action=deepcopy(action), feedback=dict(status='rejected', stage='grasp_endpoint'))


def request(original, history, *, remaining):
    result = deepcopy(original)
    body = json.loads(result['messages'][1]['content'])
    body['history'] = deepcopy(history)
    body['budget'] = dict(decisions=remaining, planning=remaining, observations=0)
    result['messages'][0]['content'] += '''
先前意图未通过执行器抓取端点预检。根据相同观测自主重新判断，选择不同抓取意图或STOP。
反馈只说明预检未通过，不提供预设原因。不要重复已拒绝的参数；禁止修改安全阈值。
'''
    result['messages'][1]['content'] = json.dumps(body, ensure_ascii=False, separators=(',', ':'))
    return result


def permitted(action, history):
    if action['id'] == 'STOP':
        return 'model_stopped'
    if action['id'] != 'PROPOSE_GRASP':
        return 'unsupported_action'
    if any(action == row['action'] for row in history):
        return 'repeated_rejected_action'
    return 'proposal'
