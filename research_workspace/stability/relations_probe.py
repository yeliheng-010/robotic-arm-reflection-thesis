"""固定开发碰撞报告的真实9B几何关系提示试验；不导出训练样本。"""
import json
import urllib.request
from stability.experiment import OUT
from stability.prompt import parse_response
from stability.relations_prompt import build_messages
from stability.teacher import ENDPOINT
from reflection.reflector import Parameters


def main():
    directory = OUT/'relations_probe'
    directory.mkdir(exist_ok=True)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    rows = []
    for case in ('01', '03', '05'):
        result = json.loads((OUT/'train_v3'/case/'stable/result.json').read_text())
        record = result['records'][0]
        messages = build_messages(result['instruction'], record['error'], parameters=record['parameters'])
        event = {'case': case, 'messages': messages, 'purpose': 'development_only'}
        request = urllib.request.Request(ENDPOINT+'/reflect',
            data=json.dumps({'messages': messages}, ensure_ascii=False).encode(),
            headers={'Content-Type': 'application/json'})
        try:
            with opener.open(request, timeout=900) as response:
                event['response'] = json.load(response)
            event['parsed'] = parse_response(event['response']['text'],
                Parameters().updated(record['parameters'])).to_dict()
        except Exception as error:
            event['error'] = repr(error)
        with (directory/(case+'.json')).open('x') as stream:
            json.dump(event, stream, ensure_ascii=False, indent=2)
        rows.append({k: event[k] for k in ('case', 'parsed', 'error') if k in event})
    (directory/'result.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    print(json.dumps(rows, ensure_ascii=False))


if __name__ == '__main__':
    main()
