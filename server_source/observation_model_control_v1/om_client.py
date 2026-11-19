"""有限候选请求，不包含物理真值/标签，不做隐藏重试。"""
import json
import time
import urllib.request
from om_common import ROOT,PORT,ALIASES,model_identity,requested_adapter

OPENER=urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(path,payload=None):
    body=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None
    req=urllib.request.Request(f'http://127.0.0.1:{PORT}'+path,data=body,
                               headers={'Content-Type':'application/json'})
    with OPENER.open(req,timeout=180) as response:
        return json.load(response)


def payload_for(method,messages):
    assert method in ALIASES
    return dict(model=ALIASES[method],messages=messages,temperature=0,seed=42,max_tokens=128,
                chat_template_kwargs={'enable_thinking':False})


def check_response(response,method):
    assert response['model']==ALIASES[method]
    assert response['identity']==model_identity()
    assert response['active_method']==method
    assert response['active_adapter_sha256']==requested_adapter(method)
    choice=response['choices'][0]
    if choice['finish_reason']!='stop':
        raise ValueError('Incomplete generation')
    text=choice['message']['content']
    if not isinstance(text,str) or not text.strip():
        raise ValueError('Empty response')
    return text


def generate(method,messages,*,max_tokens):
    assert max_tokens==128
    event=dict(request=payload_for(method,messages),started_at=time.time())
    started=time.monotonic()
    try:
        event['response']=request('/v1/chat/completions',event['request'])
        event['text']=check_response(event['response'],method)
    except Exception as error:
        event.update(error=repr(error),service_error='response' not in event)
    event['elapsed_s']=time.monotonic()-started
    return event


def ready():
    result=request('/health')
    assert result['status']=='ready' and result['identity']==model_identity()
    assert set(result['models'])==set(ALIASES.values())
    assert set(result['reload_errors'])=={'previous159','new189'}
    assert all(value<=1e-4 for value in result['reload_errors'].values())
    assert result['replay_passed']
    return result
