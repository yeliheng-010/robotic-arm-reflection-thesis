"""仅用已发生历史构造模型输入；物理结果不得进入提示词。"""
import json
from copy import deepcopy
from cd_common import VARIANTS, HEIGHTS

SUMMARY = ('已执行一次XY抓取残差补偿，随后仍然失败；该历史不能证明残差是失败根因。'
           '请区分当前失败阶段与测量字段，选择一个尚未执行的合法候选。')
EXPERT = ('专家启发式干预：优先选择候选集中candidate_index最小的、尚未执行的'
          'exploratory_candidate动作。这是额外策略指导，并非已知成功标签。')


def request(case, variant):
    assert variant in VARIANTS
    value = deepcopy(case['request'])
    if variant == 'replay':
        return value
    body = json.loads(value['messages'][1]['content'])
    if variant == 'reverse':
        body['candidates'].reverse()
        body['legal_action_ids'].reverse()
    else:
        body['diagnostic_note'] = SUMMARY if variant == 'summary' else EXPERT
    value['messages'][1]['content'] = json.dumps(body, ensure_ascii=False, allow_nan=False)
    return value


def extra_actions(case):
    feedback = case['snapshot']['feedback']
    phase = feedback['evidence']['motion_context']['phase']
    if feedback['error_type'] != 'ik_failure' or phase != 'carry_transport':
        return []
    result = []
    for height in HEIGHTS:
        state = deepcopy(case['snapshot']['state'])
        assert state['parameters']['lift_height'] == .35
        state['parameters']['lift_height'] = height
        result.append(dict(id=f'expert_lift_{height:.2f}', kind='expert_lower_lift',
            changes=dict(lift_height=height), state=state, source='expert_diagnostic'))
    return result


def branches(cases):
    result = []
    for case_index, case in enumerate(cases):
        for action in case['candidates'] + extra_actions(case):
            result.append(dict(index=len(result), case_index=case_index,
                case_id=case['id'], action=action,
                origin='expert_extension' if action['kind']=='expert_lower_lift' else 'original_menu'))
    return result


def smoke_indices(rows, cases):
    indices = []
    for error in ('empty_grasp', 'collision', 'ik_failure'):
        case = next(c for c in cases if c['source']['error_type'] == error)
        indices.append(next(r['index'] for r in rows if r['case_id'] == case['id']
                            and r['action']['id'] == case['rule_action']['id']))
    indices.append(next(r['index'] for r in rows if r['origin'] == 'expert_extension'))
    return indices
