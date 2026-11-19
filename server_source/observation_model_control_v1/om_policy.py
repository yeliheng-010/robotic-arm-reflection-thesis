"""四组仅分离聚合方式与选择器；提示中没有审计信息。"""
from policy import observe as sensor_observe
from loopstudy.actions import candidates,choose_rule
from loopstudy.selection import messages,resolve,MAX_TOKENS
from om_common import METHODS,ALIASES
from om_client import generate,check_response


def observe(step,item,*,method,used):
    assert method in METHODS
    return sensor_observe(step,item,mode=method.split('_')[1],used=used)


def inputs(step,observation):
    feedback,state=observation['feedback'],step['state']
    rows=candidates(feedback,state,[],legacy=False)
    return dict(after_attempt=step['index'],before=state,feedback=feedback,candidates=rows,
                observation=observation)


def prompt(decision):
    return messages(decision['feedback'],decision['before'],rows=decision['candidates'],history=[])


def selection(event,rows):
    if 'response' not in event:
        raise RuntimeError('Model transport failed: '+str(event.get('error')))
    try:
        text=check_response(event['response'],'base')
    except ValueError as error:
        assert event.get('error') and 'text' not in event
        return None,repr(error)
    assert 'error' not in event and event['text']==text
    try:
        return resolve(text,rows),None
    except (ValueError,KeyError,TypeError) as error:
        return None,repr(error)


def decide(step,observation,*,method):
    assert method in METHODS
    d=inputs(step,observation)
    d.update(method=method,model=ALIASES['base'] if method.startswith('base_') else None,
             source='observation_processing_selector_control')
    if not d['candidates']:
        return dict(d,selected=None,invalid='Candidate set exhausted')
    if method.startswith('rule_'):
        return dict(d,selected=choose_rule(d['candidates'],d['before'],report=d['feedback']))
    event=generate('base',prompt(d),max_tokens=MAX_TOKENS)
    d['event']=event
    if 'response' not in event:
        return dict(d,selected=None,service_failure=True,invalid=str(event.get('error')))
    selected,invalid=selection(event,d['candidates'])
    d['selected']=selected
    if invalid:
        d['invalid']=invalid
    return d
