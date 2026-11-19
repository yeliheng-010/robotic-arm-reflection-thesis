"""复用原物理审计，独立重建4B请求并核对服务端双日志。"""
import importlib
from unittest.mock import patch
from common import ROOT,read
from client import payload_for,check_response
from loopstudy.selection import messages,resolve
from loopstudy import audit as previous


def model_check(decision,history,*,method):
    event=decision['event']
    prompt=messages(decision['feedback'],decision['before'],rows=decision['candidates'],history=history)
    assert event['request']==payload_for(method,prompt)
    if 'response' in event:
        response=event['response']
        identifier=response['id']
        assert isinstance(identifier,str) and len(identifier)==32 and all(c in '0123456789abcdef' for c in identifier)
        saved=read(ROOT/'service/requests'/f'{identifier}.json')
        assert saved==dict(request=event['request'],response=response)
        if 'error' not in event:
            assert event['text']==check_response(response,method)
    else:
        assert event.get('error') and event.get('service_error')
    if decision['selected'] is not None:
        assert 'error' not in event and resolve(event['text'],decision['candidates'])==decision['selected']
    else:
        assert decision.get('invalid')
        if 'error' not in event:
            try:
                resolve(event['text'],decision['candidates'])
            except (ValueError,KeyError,TypeError):
                return
            raise AssertionError('Valid model selection incorrectly rejected')


def audit(result,entry):
    method=entry['method']
    module=importlib.import_module(entry['package']+'.audit')
    def check(decision,history):
        return model_check(decision,history,method=method)
    with patch.object(previous,'model_check',check):
        checked=module.audit(result,entry['item'])
    return checked
