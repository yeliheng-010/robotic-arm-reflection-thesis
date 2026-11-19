"""从原始反馈、选择和物理记录独立重建执行链。"""
import json
import random
import numpy as np
from controlled.worker import jsonlines
from controlled.feedback import check_action
from controlled.config import MAX_TOKENS
from reflection.reflector import Parameters
from flashnext.client import check_response,parse_correction
from refinement.audit import emitted,compare_saved
from bounded.candidates import candidates
from bounded.selection import payload,resolve
from bounded.baselines import priority
from nextstudy.prompt import messages
from recovery.design import configuration,MAX_ATTEMPTS,SELECTION_SEED,sequence_changes
from recovery.feedback import project
from recovery.methods import choose_stage
from recovery.protocol import reference_path

TOLERANCE = 1e-8


def counts(result,events):
    records = result['records']
    calls = sum('reflection' in r or 'reflection_error' in r for r in records)
    errors = sum('reflection_error' in r for r in records)
    services = sum(bool(e.get('service_error')) for e in events)
    assert services<=errors
    return dict(calls=calls,invalid=errors-services,service_errors=services,
                model_latency_s=sum(e.get('elapsed_s',0) for e in events))


def choices(directory,arm):
    name = 'baseline_choices.jsonl'
    if arm=='hybrid':
        name = 'selection.jsonl'
    elif arm=='guided':
        name = 'requests.jsonl'
    elif arm in ('candidate_depth','depth_candidate'):
        name = 'sequence.jsonl'
    return jsonlines(directory/name)


def records_check(result,item):
    assert result['scenario']==configuration(item) and result['item']==item
    assert result['test_used'] is False and result['training_approved'] is False
    assert all(result[k]==item[k] for k in ('source','destination','fault','seed'))
    rows = result['records']
    assert 1<=len(rows)==result['attempts']<=MAX_ATTEMPTS
    assert result['success']==any(r['accepted'] for r in rows)
    assert all(not r['accepted'] or r['physical_success'] for r in rows)
    original = json.loads(reference_path(item).read_text())
    compare_saved(result,original)
    assert rows[0]['domain_randomization']==original['records'][0]['domain_randomization']
    for index,row in enumerate(rows):
        assert row['attempt']==index+1
        for field in ('initial_qpos','initial_body_xyz'):
            np.testing.assert_allclose(rows[0]['candidate_trace'][field],row['candidate_trace'][field],atol=TOLERANCE,rtol=0)
        available = row['diagnostics'].get('available_candidate_count',0)
        if available:
            assert row['parameters']['candidate_index']==row['diagnostics']['selected_candidate_index']
    for before,after in zip(rows,rows[1:]):
        expected = Parameters().updated(before['parameters']).updated(before.get('reflection',{}).get('changes',{}))
        assert expected==Parameters().updated(after['parameters'])
    if item['study']=='collision':
        error = rows[0]['error']
        assert error['error_type']=='collision'
        assert any('SafetyDivider' in p for p in error['evidence']['contacts'])
        assert rows[0]['diagnostics']['motion_segment']=='transport'


def model_check(event,record,*,item,projected,history,result):
    values = record['parameters']
    if item['arm']=='hybrid':
        rows = candidates(emitted(projected),values,history)
        assert rows==event['candidates']
        assert event['request']==payload(emitted(projected),values,rows=rows,history=history)
        if 'reflection' in record:
            assert event['text']==check_response(event['response'])
            assert resolve(event['text'],rows)==event['parsed']==record['reflection']
    else:
        expected = messages(result['instruction'],emitted(projected),parameters=values,history=history,variant='guided')
        assert event['request']['messages']==expected
        assert event['request']['max_tokens']==MAX_TOKENS
        assert event['request']['temperature']==0 and event['request']['seed']==42
        if 'reflection' in record:
            parameters = Parameters().updated(values)
            count = projected['evidence']['diagnostics'].get('available_candidate_count')
            answer = parse_correction(check_response(event['response']),parameters,candidate_count=count)
            check_action(answer,parameters,candidate_count=count)
            assert answer.to_dict()==event['parsed']==record['reflection']
    if 'reflection_error' in record:
        assert event.get('error')


def rule_check(event,record,*,item,projected,history,rng):
    parameters = Parameters().updated(record['parameters'])
    assert event['model'] is None
    if item['arm'] in ('candidate_depth','depth_candidate'):
        expected = sequence_changes(item['arm'],parameters,step=len(history))
        assert event['mode']==item['arm'] and event['step']==len(history)
        assert record['reflection']['changes']==expected
    else:
        rows = candidates(emitted(projected),record['parameters'],history)
        assert rows==event['candidates']
        if item['arm']=='random':
            selected = rng.choice(rows)
        elif item['arm']=='rule_stage':
            selected = choose_stage(rows,parameters,report=emitted(projected))
        else:
            selected = min(rows,key=lambda r:priority(r,parameters))
        assert selected['id']==event['selected']
        assert selected['changes']==record['reflection']['changes']
        assert selected['explanation']==record['reflection']['cause']
    assert event['answer']==record['reflection']


def audit(directory,result,item):
    records_check(result,item)
    records = [r for r in result['records'] if 'reflection' in r or 'reflection_error' in r]
    feedback,events = jsonlines(directory/'feedback.jsonl'),choices(directory,item['arm'])
    assert len(records)==len(feedback)==len(events)
    history,rng = [],random.Random(SELECTION_SEED+item['seed'])
    for record,shown,event in zip(records,feedback,events):
        projected = project(record['error'],result['scenario'],attempt=record['attempt'])
        assert shown['projected']==projected and shown['history']==history
        if item['arm'] in ('hybrid','guided'):
            model_check(event,record,item=item,projected=projected,history=history,result=result)
        else:
            rule_check(event,record,item=item,projected=projected,history=history,rng=rng)
        if 'reflection' in record:
            assert shown['answer']==record['reflection']
            history.append(dict(error=projected,reflection=record['reflection']))
        else:
            assert shown.get('error')
    return dict(passed=True,initial_and_first_outcome_paired=True,projected_history_verified=True,
                executed_actions_verified=True,**counts(result,events))
