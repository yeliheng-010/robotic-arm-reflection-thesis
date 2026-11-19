from f_response import finish
from sv_common import ROOT, read, sha
from sv_actions import validate, choose


def proposal(event, bundle, *, case, method):
    if method == 'fixed_rule':
        assert event['status'] == 'proposed' and event['action'] == choose(bundle['request'])
        return event['action']
    assert event['status'] != 'policy_error', event
    model = event['model']
    key = f"{case['item']['id']}_{method}_{event['index']}"
    folder = ROOT/'service/requests'
    assert read(folder/(key+'_request.json')) == dict(condition=case['item']['id'], mode=method,
        ordinal=event['index'], request=bundle['request'], messages=bundle[method+'_messages'], visual=bundle['visual'])
    saved = read(folder/(key+'_response.json'))
    assert {k:v for k,v in model.items() if k != 'validation'} == saved
    assert saved['manifest_sha256'] == sha(ROOT/'manifest.json')
    encoding = read(folder/(key+'_generation_started.json'))['encoding']
    assert encoding == saved['encoding'] and len(encoding['image_grid_thw']) == 2
    assert encoding['pixel_values_shape'][0] == sum(g[0]*g[1]*g[2] for g in encoding['image_grid_thw'])
    response = model['response']
    assert response['identity'] == read(ROOT/'service/ready.json')['identity']
    assert response['identity']['adapter_enabled'] is False
    assert response['finish_reason'] == finish(response['generated_ids'], response['eos_ids'])
    checked = validate(response, bundle['request'], mode=method)
    assert checked == model['validation']
    if not checked['valid']:
        assert event['status'] == 'invalid_output' and 'action' not in event
        return None
    assert event['status'] == 'proposed' and event['action'] == checked['parsed']['action']
    return event['action']
