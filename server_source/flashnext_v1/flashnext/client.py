"""共享模型 API 接入；原始请求留档，非法修正不进入执行器。"""
import json
from pathlib import Path
import time
import urllib.request
from stability.prompt import build_messages, parse_response

MODEL = 'qwen3.8-flash-next'
BASE = 'http://127.0.0.1:8080/v1'
TIMEOUT = 180
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(path, payload=None):
    body = json.dumps(payload, ensure_ascii=False).encode() if payload else None
    req = urllib.request.Request(BASE+path, data=body,
                                 headers={'Content-Type': 'application/json'})
    with OPENER.open(req, timeout=TIMEOUT) as response:
        return json.load(response)


def check_response(response):
    if response.get('model') != MODEL:
        raise ValueError('Unexpected model identity')
    choice = response['choices'][0]
    if choice.get('finish_reason') != 'stop':
        raise ValueError('Incomplete generation: '+str(choice.get('finish_reason')))
    text = choice['message'].get('content')
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Empty model response')
    return text


def parse_correction(text, parameters, *, candidate_count=None):
    answer = parse_response(text, parameters)
    if ('candidate_index' in answer.changes and candidate_count is not None
            and answer.changes['candidate_index'] >= candidate_count):
        raise ValueError('Unavailable candidate index')
    return answer


def generate(messages, *, max_tokens):
    payload = dict(model=MODEL, messages=messages, temperature=0, seed=42,
                   max_tokens=max_tokens, chat_template_kwargs={'enable_thinking': False})
    event = {'request': payload, 'started_at': time.time()}
    start = time.monotonic()
    try:
        event['response'] = request('/chat/completions', payload)
        event['text'] = check_response(event['response'])
    except Exception as error:
        event.update(error=repr(error), service_error='response' not in event)
    event['elapsed_s'] = time.monotonic()-start
    return event


def ready():
    result = request('/models')
    assert any(m['id'] == MODEL and m.get('status', {}).get('value') == 'loaded'
               for m in result['data']), 'Model is not loaded'
    return result


def append(path, event):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as stream:
        stream.write(json.dumps(event, ensure_ascii=False)+'\n')
        stream.flush()


class FlashReflector:
    def __init__(self, instruction, directory, *, max_tokens=1024):
        self.instruction = instruction
        self.path = Path(directory)/'requests.jsonl'
        self.max_tokens = max_tokens

    def reflect(self, report, parameters, history=()):
        previous = [{'error': r['error'], 'reflection': {k: r['reflection'][k]
                    for k in ('cause', 'changes')}} for r in history]
        messages = build_messages(self.instruction, report.to_dict(),
                                  parameters=parameters.to_dict(), history=previous)
        event = generate(messages, max_tokens=self.max_tokens)
        try:
            if 'error' in event:
                raise ValueError(event['error'])
            count = report.evidence.get('diagnostics', {}).get('available_candidate_count')
            answer = parse_correction(event['text'], parameters, candidate_count=count)
            event['parsed'] = answer.to_dict()
            return answer
        except Exception as error:
            event['error'] = repr(error)
            raise RuntimeError('Flash-Next reflection failed: '+str(error)) from error
        finally:
            append(self.path, event)

