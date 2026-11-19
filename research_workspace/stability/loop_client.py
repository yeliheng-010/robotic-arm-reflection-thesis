"""保留真实提示、响应和解析失败，不回退规则、不修补模型输出。"""
import json
from pathlib import Path
import urllib.request
from stability.prompt import build_messages, parse_response
from stability.loop_protocol import PORT, validate_reply


class LoopReflector:
    def __init__(self, instruction, directory, *, arm):
        self.instruction, self.arm = instruction, arm
        self.path = Path(directory)/'requests.jsonl'
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def reflect(self, report, parameters, *previous_history):
        history = previous_history[0] if previous_history else ()
        previous = [{'error': r['error'], 'reflection': {k: r['reflection'][k]
                    for k in ('cause', 'changes')}} for r in history]
        messages = build_messages(self.instruction, report.to_dict(),
            parameters=parameters.to_dict(), history=previous)
        event = {'arm': self.arm, 'messages': messages}
        request = urllib.request.Request(f'http://127.0.0.1:{PORT}/reflect',
            data=json.dumps(dict(arm=self.arm, messages=messages), ensure_ascii=False).encode(),
            headers={'Content-Type': 'application/json'})
        try:
            with self.opener.open(request, timeout=900) as response:
                event['response'] = json.load(response)
            validate_reply(event['response'], self.arm)
            answer = parse_response(event['response']['text'], parameters)
            event['parsed'] = answer.to_dict()
            return answer
        except Exception as error:
            event['error'] = str(error)
            event['service_error'] = 'response' not in event
            raise RuntimeError('Model call or parse failed: '+str(error)) from error
        finally:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open('a') as stream:
                stream.write(json.dumps(event, ensure_ascii=False)+'\n')
