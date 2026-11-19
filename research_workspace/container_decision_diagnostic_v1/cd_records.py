"""模型环境可导入的严格解析与请求审计。"""
import json
from cd_common import ROOT, VARIANTS, read
from cd_client import check_response
from cd_design import request


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def parse(text, rows):
    parsed = json.loads(text,object_pairs_hook=unique)
    if not isinstance(parsed,dict) or set(parsed) != {'action_id'}:
        raise ValueError('Expected exactly action_id')
    matched = [r for r in rows if r['id']==parsed['action_id']]
    if len(matched) != 1:
        raise ValueError('Unknown action; no fallback')
    return matched[0]


def decode(response, case):
    value = dict(valid=False,action=None,invalid=None)
    try:
        text = check_response(response)
        value.update(valid=True,action=parse(text,case['candidates']))
    except (ValueError,TypeError,KeyError) as error:
        value['invalid'] = repr(error)
    return value


def tasks(manifest):
    return [dict(id=case['id']+'__'+variant,case_index=i,variant=variant)
            for i,case in enumerate(manifest['cases']) for variant in VARIANTS]


def audit_record(record, task, manifest):
    case = manifest['cases'][task['case_index']]
    assert record['task'] == task and record['request'] == request(case,task['variant'])
    response = record['response']
    ledger = read(ROOT/'service/requests'/f"{response['id']}.json")
    assert ledger == dict(request=record['request'],response=response)
    expected = decode(response,case)
    assert record['result'] == expected
    if task['variant'] == 'replay':
        assert check_response(response) == case['original_text'], 'Original choice replay changed'
        assert expected['action'] == case['model_action']
    return expected
