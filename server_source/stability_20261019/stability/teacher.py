"""真实模型请求逐条落盘；拒绝修补、缓存或规则回退。"""
import json
from pathlib import Path
import urllib.request
from stability.prompt import build_messages, parse_response

ENDPOINT = 'http://127.0.0.1:18823'


def health():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(ENDPOINT+'/health', timeout=10) as response:
        return json.load(response)


class AuditedTeacher:
    def __init__(self, instruction, directory):
        self.instruction = instruction
        self.path = Path(directory)/'requests.jsonl'
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def reflect(self, report, parameters, history=()):
        messages = build_messages(self.instruction, report.to_dict(),
                                  parameters=parameters.to_dict(), history=history)
        event = {'messages': messages}
        request = urllib.request.Request(ENDPOINT+'/reflect',
            data=json.dumps({'messages': messages}, ensure_ascii=False).encode(),
            headers={'Content-Type': 'application/json'})
        try:
            with self.opener.open(request, timeout=900) as response:
                event['response'] = json.load(response)
            answer = parse_response(event['response']['text'], parameters)
            event['parsed'] = answer.to_dict()
            return answer
        except Exception as error:
            event['error'] = str(error)
            raise RuntimeError('Teacher call/parse failed: '+str(error)) from error
        finally:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open('a') as stream:
                stream.write(json.dumps(event, ensure_ascii=False)+'\n')

