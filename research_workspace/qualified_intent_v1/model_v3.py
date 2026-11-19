"""显式区分参数选项与输出标量；不替模型决定抓取参数。"""
import json
import sys
from unittest.mock import patch
from qualified_intent_v1 import model
from qualified_intent_v1.common import ROOT, read, save, sha
from qualified_intent_v1.model_v2 import OUTPUT as PREVIOUS, verified as prior

OUTPUT = ROOT/'run_v3'
CLARIFICATION = '''
注意：allowed_values中的数组仅列出可选值，绝对不能复制为动作参数。
如果选择PROPOSE_GRASP，必须自主为每个字段选定一个标量：
region是一个字符串；depth_mm、tilt_deg、azimuth_deg、symmetry_deg各是一个整数。
args必须且仅含这五个字段。任何数组参数均无效，将不会执行。
根据当前观测自行取舍；本提示没有指定哪组参数正确。不确定可选择STOP。
'''


def prepare():
    previous = prior()
    entries, identities = [], dict(previous['identities'])
    for entry in previous['entries']:
        seed = entry['seed']
        request = read(entry['request'])
        body = json.loads(request['messages'][1]['content'])
        for action in body['actions']:
            action['allowed_values'] = action.pop('args_spec')
        body['output_constraint'] = 'Each args field must be ONE selected scalar, never the allowed-value array.'
        request['messages'][0]['content'] += CLARIFICATION
        request['messages'][1]['content'] = json.dumps(body, ensure_ascii=False, separators=(',', ':'))
        save(OUTPUT/f'{seed}/request.json', request)
        entries.append(dict(entry, request=str(OUTPUT/f'{seed}/request.json')))
        for name in ('response.json', 'validated.json'):
            path = PREVIOUS/str(seed)/name
            identities[str(path)] = sha(path)
    paths = [ROOT/'model_v3.py', ROOT/'run_v3.sbatch', *OUTPUT.rglob('request.json')]
    identities.update({str(p): sha(p) for p in paths})
    save(OUTPUT/'manifest.json', dict(previous, entries=entries, identities=identities,
        predecessor=str(PREVIOUS), change='Explicit scalar output instructions only; same observations and action bounds',
        max_model_calls=2, scope='paired_development_prompt_repair_not_heldout_validation'))


def verified():
    value = read(OUTPUT/'manifest.json')
    assert all(sha(p) == h for p, h in value['identities'].items())
    return value


def run():
    with patch.object(model, 'RUN', OUTPUT), patch.object(model, 'verify', verified):
        model.main()


if __name__ == '__main__':
    {'prepare': prepare, 'run': run}[sys.argv[1]]()
