import json
import urllib.request
from sv_common import ROOT, PORT, sha
from sv_actions import validate


def generate(bundle, *, condition, method, ordinal):
    body = dict(condition=condition, mode=method, ordinal=ordinal, request=bundle['request'],
        messages=bundle[method+'_messages'], visual=bundle['visual'])
    request = urllib.request.Request(f'http://127.0.0.1:{PORT}/generate',
        data=json.dumps(body, ensure_ascii=False, allow_nan=False).encode(),
        headers={'Content-Type': 'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=300) as response:
        event = json.load(response)
    assert event['manifest_sha256'] == sha(ROOT/'manifest.json')
    checked = validate(event['response'], bundle['request'], mode=method)
    return dict(event, validation=checked)
