"""核验混合来源、模型选择、数值编译、物理配对和原数据。"""
import argparse
import ast
import json

import numpy as np
from reflection.reflector import Parameters, stable_error
from training.refine.prompt import parse_response
from training.refine.verify import check_originals
from decision.candidates import build_candidates
from decision.experiment import OUT, fingerprints, compact
from decision.selector import parse_choice


def read(path):
    return json.loads(path.read_text())


def first_signature(result):
    record = result['records'][0]
    return {k: record[k] for k in ('parameters', 'accepted', 'physical_success')} | {
        'error': (record['error'] or {}).get('error_type')}


def check_hybrid(result, directory):
    path = directory / 'choices.jsonl'
    events = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    records = [r for r in result['records'] if 'reflection' in r or 'reflection_error' in r]
    assert len(events) == len(records)
    for event, record in zip(events, records):
        payload = json.loads(event['messages'][1]['content'])
        assert payload['error'] == stable_error(record['error'])
        assert payload['parameters'] == record['parameters']
        assert payload['carried_body'] == result['source']
        params = Parameters().updated(record['parameters'])
        choices = build_candidates(record['error'], params, source=result['source'])
        assert choices == event['candidates'] == payload['candidates']
        if 'reflection' in record:
            parsed = parse_choice(event['response']['text'], choices).to_dict()
            assert parsed == record['reflection'] == event['compiled']
            assert parsed['source'] == 'hybrid_llm_selector'
        else:
            assert event['error'] == record['reflection_error']


def model_match(event, record):
    if 'response' not in event:
        return False
    payload = json.loads(event['request']['messages'][1]['content'])
    if payload['error'] != stable_error(record['error']) or payload['parameters'] != record['parameters']:
        return False
    try:
        answer = parse_response(event['response']['text'], Parameters().updated(record['parameters']))
    except (ValueError, TypeError):
        return False
    return answer.to_dict() == record['reflection']


def check_result(result, *, arm, events):
    records = result['records']
    assert result['success'] == any(r['accepted'] for r in records)
    assert result['attempts'] == len(records) <= 3
    expected = {'llm': 'llm', 'rule': 'rule', 'hybrid': 'hybrid_llm_selector'}
    for index, record in enumerate(records):
        assert not record['accepted'] or record['physical_success']
        if arm == 'retry':
            assert 'reflection' not in record and record['parameters'] == records[0]['parameters']
        if 'reflection' not in record:
            continue
        answer = record['reflection']
        assert answer['source'] == expected[arm]
        updated = Parameters().updated(record['parameters']).updated(answer['changes']).to_dict()
        assert json.loads(json.dumps(updated)) == records[index + 1]['parameters']
        if arm == 'llm':
            assert any(model_match(event, record) for event in events)


def check_group(directory, task, *, arms, events):
    results = []
    for arm in arms:
        result = read(directory / arm / 'result.json')
        for key in ('source', 'destination', 'fault', 'seed', 'instruction'):
            assert task[key] == result[key], key
        check_result(result, arm=arm, events=events)
        if arm == 'hybrid':
            check_hybrid(result, directory / arm)
        results.append(result)
    for result in results[1:]:
        assert first_signature(results[0]) == first_signature(result)
        np.testing.assert_allclose(results[0]['records'][0]['evaluation']['position'],
                                   result['records'][0]['evaluation']['position'], atol=1e-8, rtol=0)
    return results


def audit_code():
    for path in (OUT / 'decision').glob('*.py'):
        source = path.read_text()
        assert len(source.splitlines()) <= 300, path.name
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno - node.lineno + 1 <= 50, (path.name, node.name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    directory = OUT / args.run
    manifest = read(directory / 'manifest.json')
    assert manifest['code_sha256'] == fingerprints()
    events = [json.loads(s) for s in (OUT / 'teacher/requests.jsonl').read_text().splitlines()]
    rows = read(directory / 'result.json')
    assert len(rows) == len(manifest['tasks']) * len(manifest['arms'])
    for index, task in enumerate(manifest['tasks']):
        case = f'{index:02d}'
        results = check_group(directory / case, task, arms=manifest['arms'], events=events)
        for arm, result in zip(manifest['arms'], results):
            assert compact(result, case=case, arm=arm) in rows
    audit_code()
    totals = {arm: {'success': sum(r['success'] for r in rows if r['arm'] == arm),
                   'tasks': sum(r['arm'] == arm for r in rows)} for arm in manifest['arms']}
    output = {'status': 'passed', 'totals': totals, 'original_results_unchanged': check_originals(),
              'original_code_and_dataset_hashes_unchanged': True, 'test_samples_read': 0,
              'hybrid_outputs_kept_separate': True, 'paired_cases': len(manifest['tasks'])}
    (directory / 'verification.json').write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

