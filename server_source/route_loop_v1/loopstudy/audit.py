"""重新读取原始物理与决策记录，检查状态映射及公共预算。"""
import json
from pathlib import Path
import numpy as np
import spatialmath as sm
from flashnext.client import check_response,MODEL
from semanticfix2.context import enrich,project
from semanticfix2.audit import audit_contacts
from semanticfix2.protocol import sha
from loopstudy.actions import initial,candidates,choose_rule,PROFILES
from loopstudy.selection import messages,resolve,MAX_TOKENS
from loopstudy.design import MAX_ATTEMPTS,configuration


def adapter_check(record,state):
    assert record['executor_state']==state and record['parameters']==state['parameters']
    trace = record['execution_adapter']
    if not trace:
        assert not record['accepted']
        return False
    assert trace['profile']==state['profile'] and trace['yaw_deg']==PROFILES[state['profile']]
    assert trace['observation_state_unchanged'] and trace['keep_orientation']==(trace['yaw_deg']==0)
    start,hover,target = np.array(trace['start']),np.array(trace['planned_poses'][1]),np.array(trace['planned_poses'][2])
    np.testing.assert_allclose(start[:3,:3],hover[:3,:3],atol=1e-12,rtol=0)
    expected = sm.SO3.Rz(trace['yaw_deg'],unit='deg').R@start[:3,:3]
    np.testing.assert_allclose(expected,target[:3,:3],atol=1e-12,rtol=0)
    np.testing.assert_allclose(trace['target_xyz'],target[:3,3],atol=1e-12,rtol=0)
    assert trace['lift_height']==state['parameters']['lift_height']
    assert trace['durations']==[0.0]+[state['parameters']['time_scale']]*3
    return True


def physical(step,item,reference):
    path = Path(step['result_path'])
    assert sha(path)==step['result_sha256']
    result = json.loads(path.read_text())
    assert result['attempts']==len(result['records'])==1 and not result['llm_stats']
    record = result['records'][0]
    assert step['success']==result['success']==record['accepted']
    entered = adapter_check(record,step['state'])
    if step['success']:
        assert record['physical_success'] and record['error'] is None
        assert all(record['evaluation'][k] for k in ('inside_xy','inside_z','supported','settled'))
    audit_contacts(record['error'])
    for field in ('initial_qpos','initial_body_xyz'):
        np.testing.assert_allclose(reference['candidate_trace'][field],record['candidate_trace'][field],atol=1e-8,rtol=0)
    error = record['error']
    expected = project(enrich(error,attempt=step['index']),configuration(item),attempt=step['index']) if error else None
    assert expected==step['feedback']
    return record,entered


def model_check(decision,history):
    event = decision['event']
    expected = dict(model=MODEL,messages=messages(decision['feedback'],decision['before'],
        rows=decision['candidates'],history=history),temperature=0,seed=42,max_tokens=MAX_TOKENS,
        chat_template_kwargs={'enable_thinking':False})
    assert event['request']==expected
    if 'error' not in event:
        assert event['text']==check_response(event['response'])
    if decision['selected'] is not None:
        assert resolve(event['text'],decision['candidates'])==decision['selected']
        assert 'error' not in event and 'invalid' not in decision
    else:
        assert decision.get('invalid')


def decision_check(decision,item,history):
    if item['arm']=='retry':
        assert decision['candidates']==[] and decision['selected']['state']==decision['before']
        assert decision.get('model') is None and 'event' not in decision
        return
    report,state = decision['feedback'],decision['before']
    rows = candidates(report,state,history,legacy=item['arm']=='old_rule')
    assert rows==decision['candidates']
    if not rows:
        assert decision['selected'] is None and decision.get('invalid')
    elif item['arm']=='hybrid':
        model_check(decision,history)
    else:
        assert decision['selected']==choose_rule(rows,state,report=report,legacy=item['arm']=='old_rule')
        assert decision.get('model') is None and 'event' not in decision


def audit(result,item):
    assert result['item']==item and result['scenario']==configuration(item)
    assert result['training_approved'] is False and result['test_used'] is False
    steps,decisions = result['attempts'],result['decisions']
    assert 1<=len(steps)<=MAX_ATTEMPTS and len(decisions)<=MAX_ATTEMPTS-1
    reference = json.loads(Path(steps[0]['result_path']).read_text())['records'][0]
    state,entered_count = initial(),0
    for offset,step in enumerate(steps):
        assert step['index']==offset+1 and step['state']==state
        record,entered = physical(step,item,reference)
        entered_count += entered
        if offset<len(decisions):
            decision = decisions[offset]
            assert not step['success'] and decision['after_attempt']==step['index']
            assert decision['before']==state and decision['feedback']==step['feedback']
            decision_check(decision,item,decisions[:offset])
            state = decision['selected']['state'] if decision['selected'] else None
    assert result['success']==steps[-1]['success'] and not any(s['success'] for s in steps[:-1])
    invalid = sum(d['selected'] is None for d in decisions)
    service = sum(bool(d.get('event',{}).get('service_error')) for d in decisions)
    assert result['status']==('service_error' if service else 'invalid' if invalid else 'completed')
    if invalid:
        assert invalid==1 and len(decisions)==len(steps) and state is None and not result['success']
    else:
        assert len(decisions)==len(steps)-1 and (result['success'] or len(steps)==MAX_ATTEMPTS)
    return dict(passed=True,attempts=len(steps),calls=sum('event' in d for d in decisions),invalid=invalid,
        service_errors=service,adapter_entries=entered_count)
