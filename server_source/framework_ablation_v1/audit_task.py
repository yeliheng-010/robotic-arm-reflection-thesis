"""重新构建策略输入、候选和物理证据；不复用运行时的选择结果。"""
import importlib
from common import ROOT,read
from client import payload_for,check_response
from policy import configured,rows_for,prompt_for
from loopstudy.actions import choose_rule
from loopstudy.selection import resolve


def model_check(decision,history,*,method):
    event=decision['event']
    assert event['request']==payload_for('base',prompt_for(decision,history,method=method))
    if 'response' in event:
        response=event['response']
        identifier=response['id']
        assert len(identifier)==32 and all(c in '0123456789abcdef' for c in identifier)
        assert read(ROOT/'service/requests'/f'{identifier}.json')==dict(request=event['request'],response=response)
        if 'error' not in event:
            assert event['text']==check_response(response,'base')
    else:
        assert event.get('error') and event.get('service_error')
    if decision['selected'] is not None:
        assert 'error' not in event and 'invalid' not in decision
        assert resolve(event['text'],decision['candidates'])==decision['selected']
    else:
        assert decision.get('invalid')
        if 'error' not in event:
            try:
                resolve(event['text'],decision['candidates'])
            except (ValueError,KeyError,TypeError):
                return
            raise AssertionError('Valid model selection rejected')


def decision_check(decision,history,*,method):
    state,report=decision['before'],decision['feedback']
    if method=='retry':
        assert decision['candidates']==[]
        assert decision['selected']==dict(id='retry',state=state,changes={},kind='retry')
        assert decision.get('model') is None and 'event' not in decision
        assert decision['source']=='fixed_parameter_retry'
        return
    rows=rows_for(report,state)
    assert decision['candidates']==rows
    if not rows:
        assert decision['selected'] is None and decision.get('invalid') and 'event' not in decision
    elif method=='rule':
        assert decision['selected']==choose_rule(rows,state,report=report)
        assert decision.get('model') is None and 'event' not in decision
        assert decision['source']=='history_free_stage_rule'
    else:
        assert decision['source']==method+'_base_model'
        model_check(decision,history,method=method)


def audit(result,entry):
    module=importlib.import_module(entry['package']+'.audit')
    def check(decision,item,history):
        return decision_check(decision,history,method=entry['method'])
    with configured(entry,checker=check):
        return module.audit(result,entry['item'])
