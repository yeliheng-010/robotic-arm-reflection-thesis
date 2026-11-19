"""共享无历史候选，只有history方法向基础模型展示过去决策。"""
from contextlib import contextmanager,ExitStack
from unittest.mock import patch
from loopstudy import episode,audit as original_audit
from loopstudy.actions import candidates,choose_rule
from loopstudy.selection import messages,resolve,MAX_TOKENS
from client import generate


def rows_for(report,state):
    return candidates(report,state,[],legacy=False)


def prompt_for(decision,history,*,method):
    assert method in ('current','history')
    return messages(decision['feedback'],decision['before'],rows=decision['candidates'],
                    history=history if method=='history' else [])


def decide(step,history,*,method):
    state,report=step['state'],step['feedback']
    decision=dict(after_attempt=step['index'],before=state,feedback=report)
    if method=='retry':
        return dict(decision,candidates=[],selected=dict(id='retry',state=state,changes={},kind='retry'),
                    model=None,source='fixed_parameter_retry')
    rows=rows_for(report,state)
    decision['candidates']=rows
    if not rows:
        return dict(decision,selected=None,invalid='Candidate set exhausted')
    if method=='rule':
        return dict(decision,selected=choose_rule(rows,state,report=report),model=None,
                    source='history_free_stage_rule')
    event=generate('base',prompt_for(decision,history,method=method),max_tokens=MAX_TOKENS)
    try:
        if 'error' in event:
            raise ValueError(event['error'])
        return dict(decision,selected=resolve(event['text'],rows),event=event,source=method+'_base_model')
    except (ValueError,KeyError,TypeError) as error:
        return dict(decision,selected=None,event=event,invalid=repr(error),source=method+'_base_model')


@contextmanager
def configured(entry,*,checker=None):
    def decision(item,step,history):
        return decide(step,history,method=entry['method'])
    with ExitStack() as stack:
        stack.enter_context(patch.object(episode,'MAX_ATTEMPTS',entry['max_attempts']))
        stack.enter_context(patch.object(original_audit,'MAX_ATTEMPTS',entry['max_attempts']))
        stack.enter_context(patch.object(episode,'decide',decision))
        if checker is not None:
            stack.enter_context(patch.object(original_audit,'decision_check',checker))
        yield
