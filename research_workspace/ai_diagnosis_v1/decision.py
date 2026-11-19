"""只校验模型输出；不代选动作，不调用执行器。"""
import json
from contracts import require
from action_check import check

MAX_TEXT = 240


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate key')
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError('Nonfinite JSON constant: '+value)


def short_text(value):
    return isinstance(value, str) and 0 < len(value.strip()) <= MAX_TEXT


def assessment(value, request):
    require(isinstance(value, dict) and set(value) == {'hypotheses', 'uncertainty'}, 'Bad assessment')
    require(short_text(value['uncertainty']), 'Missing uncertainty statement')
    hypotheses = value['hypotheses']
    require(isinstance(hypotheses, list) and len(hypotheses) <= 3, 'Too many hypotheses')
    identifiers = {row['id'] for row in request['evidence']}
    for row in hypotheses:
        require(isinstance(row, dict) and set(row) == {'claim', 'evidence_ids'}, 'Bad hypothesis')
        require(short_text(row['claim']), 'Bad claim')
        references = row['evidence_ids']
        require(isinstance(references, list) and all(isinstance(v, str) for v in references), 'Bad references')
        require(bool(references) and set(references) <= identifiers, 'Unknown or missing evidence reference')


def parse(text, request, *, mode):
    require(mode in ('direct', 'diagnostic'), 'Unknown comparison method')
    result = json.loads(text, object_pairs_hook=unique, parse_constant=invalid_constant)
    keys = {'action'} if mode == 'direct' else {'action', 'assessment', 'expected_observation'}
    require(isinstance(result, dict) and set(result) == keys, 'Unexpected output fields')
    check(result['action'], request)
    if mode == 'diagnostic':
        assessment(result['assessment'], request)
        require(short_text(result['expected_observation']), 'Missing predicted observable change')
    return result
