"""本轮本地生成接口与审计格式，不启动HTTP共享服务。"""
from od_common import ALIAS,identity

MAX_TOKENS=128


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
