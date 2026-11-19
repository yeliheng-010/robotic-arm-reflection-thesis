"""模型诊断请求确定构造与逐项账本重建。"""
import json
from am_policy import context,parse
from ap_sensor import sample
from od_common import ROOT,read,LEVELS,MAX_CALLS
from od_source import source_input
from od_prompts import variant,VARIANTS,parse_probe,probe_expected,execution_prompt
from od_api import payload,check_response


def tasks(manifest):
    values=[]
    for row in manifest['rows']:
        variants=VARIANTS+(('comprehension',) if row['method']=='base_current' else ())
        for name in variants:
            values.append(dict(id=row['id']+'__'+name,kind='probe' if name=='comprehension' else 'choice',
                row=row,variant=name))
    for case in manifest['cases']:
        for level in LEVELS:
            values.append(execution_task(case,level))
    assert len(values)==MAX_CALLS and len({v['id'] for v in values})==MAX_CALLS
    return values


def execution_task(case,level):
    return dict(id=f"exec__{case['case_id']}__l{level}",kind='execute',row=case,level=level)


def observed(case,level):
    assert level in LEVELS
    source=source_input(case)
    before=source['decision']['choices'][0]['context']
    assert before['remaining_observations']==2 and source['decision']['observation']['extra_cost']==0
    samples=[sample(source['step'],source['trace']['item'],number=n) for n in range(level+1)]
    value=context(source['step'],samples,used=level)
    return dict(samples=samples,context=value,source=source)


def prepare(task):
    if task['kind']=='execute':
        return execution_prompt(observed(task['row'],task['level'])['context'])
    return variant(source_input(task['row'])['messages'],task['variant'])


def decode(task,messages,response):
    value=dict(valid=False,action=None,probe=None,correct=None,invalid=None)
    try:
        text=check_response(response)
        body=json.loads(messages[1]['content'])
        if task['kind']=='probe':
            value['probe']=parse_probe(text)
            value['correct']=value['probe']==probe_expected(body)
        else:
            value['action']=parse(text,body)
        value['valid']=True
    except (ValueError,KeyError,TypeError) as error:
        value['invalid']=repr(error)
    return value


def audit_record(record,task):
    messages=prepare(task)
    assert record['task']==task and record['request']==payload(messages)
    response=record['response']
    identifier=response['id']
    assert len(identifier)==32 and all(c in '0123456789abcdef' for c in identifier)
    ledger=read(ROOT/'service/requests'/f'{identifier}.json')
    assert ledger==dict(request=record['request'],response=response)
    assert record['result']==decode(task,messages,response)
    if task.get('variant')=='baseline':
        original=source_input(task['row'])['decision']['choices'][0]['event']
        assert check_response(response)==original['text'],'Original prompt replay changed'
    return record['result']


def load_record(task):
    record=read(ROOT/'model_records'/f"{task['id']}.json")
    audit_record(record,task)
    return record
