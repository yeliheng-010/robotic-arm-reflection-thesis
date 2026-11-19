"""localhost模型请求无重试；失败也计一次策略决策并终止分支。"""
import json
import urllib.request
from f_response import validate
from nc_common import PORT, ROOT, read, sha

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def generate(bundle, *, condition, method, ordinal):
    body = dict(condition=condition, mode=method, ordinal=ordinal, request=bundle['request'],
                messages=bundle[method+'_messages'])
    request = urllib.request.Request(f'http://127.0.0.1:{PORT}/generate',
        data=json.dumps(body, ensure_ascii=False, allow_nan=False).encode(),
        headers={'Content-Type': 'application/json'})
    with OPENER.open(request, timeout=300) as response:
        event = json.load(response)
    assert event['manifest_sha256'] == sha(ROOT/'manifest.json')
    checked = validate(event['response'], bundle['request'], mode=method)
    return dict(event, validation=checked)
