"""严格解析模型输出；不修补答案，不使用规则回退或响应缓存。"""
import json
import urllib.request

from training.refine.prompt import build_messages, parse_response


class LocalTeacher:
    def __init__(self, instruction, endpoint):
        self.instruction, self.endpoint = instruction, endpoint
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def reflect(self, report, parameters, history=()):
        messages = build_messages(self.instruction, report.to_dict(),
                                  parameters=parameters.to_dict(), history=history)
        request = urllib.request.Request(self.endpoint + '/reflect',
            data=json.dumps({'messages': messages}, ensure_ascii=False).encode(),
            headers={'Content-Type': 'application/json'})
        try:
            with self.opener.open(request, timeout=240) as response:
                result = json.load(response)
        except Exception as error:
            raise RuntimeError('Local teacher unavailable: ' + str(error)) from error
        return parse_response(result['text'], parameters)
