"""任务模型请求不重试；身份失败与格式失败分别处理。"""
import json
import time
import urllib.request
from am_common import PORT,ALIAS,identity

MAX_TOKENS=128
OPENER=urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(path,body=None):
    data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None
    req=urllib.request.Request(f'http://127.0.0.1:{PORT}'+path,data=data,
                               headers={'Content-Type':'application/json'})
    with OPENER.open(req,timeout=240) as response:
        return json.load(response)


def payload(messages):
    return dict(model=ALIAS,messages=messages,temperature=0,seed=42,max_tokens=MAX_TOKENS,
                chat_template_kwargs={'enable_thinking':False})


def check_response(response):
    assert response['model']==ALIAS and response['identity']==identity()
    assert response['active_method']=='base' and response['active_adapter_sha256'] is None
    choice=response['choices'][0]
    if choice['finish_reason']!='stop':
        raise ValueError('Incomplete generation')
    text=choice['message']['content']
    if not isinstance(text,str) or not text.strip():
        raise ValueError('Empty response')
    return text


def generate(messages):
    event=dict(request=payload(messages),started_at=time.time())
    started=time.monotonic()
    try:
        event['response']=request('/v1/chat/completions',event['request'])
        event['text']=check_response(event['response'])
    except ValueError as error:
        event['invalid']=repr(error)
    except Exception as error:
        event['service_failure']=repr(error)
    event['elapsed_s']=time.monotonic()-started
    return event


def ready():
    value=request('/health')
    assert value['status']=='ready' and value['identity']==identity() and value['replay_passed']
    return value
