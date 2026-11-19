"""独立离线接口；不导入仿真、模型客户端或原规则策略。"""
from copy import deepcopy
from contracts import (MAX_ATTEMPTS, MAX_OBSERVATIONS, ACTIONS, SEGMENTS,
                       DESCRIPTIONS, ARGUMENTS, require, parameters, vector)


def command_evidence(record, current):
    rows = [dict(field='parameters', value=current, source='executor_command')]
    diagnostic = record.get('diagnostics', {})
    for field, allowed in (('action', ACTIONS), ('motion_segment', SEGMENTS)):
        if field in diagnostic:
            require(diagnostic[field] in allowed, 'Unknown command metadata')
            rows.append(dict(field=field, value=diagnostic[field], source='executor_command'))
    if 'commanded_tcp_xyz' in diagnostic:
        require(vector(diagnostic['commanded_tcp_xyz']), 'Bad commanded TCP')
        rows.append(dict(field='commanded_tcp_xyz', value=diagnostic['commanded_tcp_xyz'],
                         source='executor_command'))
    count = diagnostic.get('available_candidate_count')
    if count is not None:
        require(type(count) is int and count >= 0, 'Bad perception candidate count')
        rows.append(dict(field='available_candidate_count', value=count, source='perception_candidate_inventory'))
    return [dict(row, id=f'e{index+1}') for index, row in enumerate(rows)]


def catalog(supported, budget, *, evidence, finished):
    require(len(set(supported)) == len(supported), 'Duplicate supported action')
    require(set(supported) <= set(DESCRIPTIONS)-{'STOP'}, 'Unknown capability')
    rows = [dict(id='STOP', effect=DESCRIPTIONS['STOP'], args_spec={})]
    if finished or budget['executions_remaining'] == 0:
        return rows
    count = next((r['value'] for r in evidence if r['field']=='available_candidate_count'), 0)
    for action in DESCRIPTIONS:
        if action in supported:
            row = available(action, budget, count=count)
            if row is not None:
                rows.append(row)
    return rows


def available(action, budget, *, count):
    if action == 'OBSERVE' and budget['observations_remaining'] == 0:
        return None
    if action == 'SELECT_GRASP' and count == 0:
        return None
    row = dict(id=action, effect=DESCRIPTIONS[action], args_spec=ARGUMENTS[action])
    if action == 'SELECT_GRASP':
        row['count'] = count
    return row


def build_request(ledger, record, *, supported=(), observations_remaining=0):
    steps = ledger['steps']
    require(1 <= len(steps) <= MAX_ATTEMPTS, 'Invalid execution ledger')
    require(all(type(s['index']) is int for s in steps), 'Attempt index must be integer')
    require([s['index'] for s in steps] == list(range(1, len(steps)+1)), 'Invalid attempt sequence')
    require(all(type(s['success']) is bool for s in steps), 'Invalid outcome flag')
    require(not any(s['success'] for s in steps[:-1]), 'Execution after success')
    require(type(observations_remaining) is int and 0 <= observations_remaining <= MAX_OBSERVATIONS,
            'Invalid observation budget')
    current = parameters(steps[-1]['state']['parameters'])
    require(current == parameters(record['parameters']), 'Ledger and executed commands differ')
    evidence = command_evidence(record, current)
    budget = dict(executions_remaining=MAX_ATTEMPTS-len(steps), observations_remaining=observations_remaining)
    task = {key: ledger['item'][key] for key in ('source', 'destination')}
    require(all(isinstance(v, str) and v.isidentifier() and len(v) <= 40 for v in task.values()), 'Bad task')
    value = dict(version='ai-diagnosis-offline-v1', task=task, after_attempt=len(steps),
                 state=current, evidence=evidence, budget=budget,
                 actions=catalog(supported, budget, evidence=evidence, finished=steps[-1]['success']),
                 sensing_status=dict(rgb='not_attached', depth='not_attached', telemetry='not_attached'),
                 scope='command_only_offline_interface_review')
    return deepcopy(value)
