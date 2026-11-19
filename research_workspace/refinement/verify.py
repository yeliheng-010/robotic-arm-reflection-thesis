"""核验真实模型输出、物理配对、代码冻结和旧数据完整性。"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

from training.refine.prompt import parse_response
from training.refine.validate import COLLECTION, OUT, ROOT, compact, fingerprint, verify_pair
from reflection.reflector import Parameters, stable_error


def read(path):
    return json.loads(path.read_text())


def check_originals():
    audit = read(OUT.parent / 'diagnosis_20261019/audit.json')
    for entry in audit['checked_files']:
        assert hashlib.sha256(Path(entry['path']).read_bytes()).hexdigest() == entry['sha256']
    code = read(COLLECTION / 'manifest.json')['code_sha256']
    for name, digest in code.items():
        assert hashlib.sha256((COLLECTION.parent / 'code' / name).read_bytes()).hexdigest() == digest
    dataset = read(COLLECTION / 'dataset/manifest.json')['dataset_sha256']
    for name, digest in dataset.items():
        # 测试集只校验文件完整性，不解析样本。
        assert hashlib.sha256((COLLECTION / 'dataset' / (name + '.jsonl')).read_bytes()).hexdigest() == digest
    return audit['checked_tasks']


def check_result(result, arm, events):
    records = result['records']
    assert result['success'] == any(r['accepted'] for r in records)
    assert len(records) <= 3
    for record in records:
        assert not record['accepted'] or record['physical_success']
        if arm == 'retry':
            assert 'reflection' not in record
            assert record['parameters'] == records[0]['parameters']
        if 'reflection' in record:
            assert record['reflection']['source'] == 'llm'
            assert any(matches(event, record) for event in events)


def matches(event, record):
    if 'response' not in event:
        return False
    request = json.loads(event['request']['messages'][1]['content'])
    if request['parameters'] != record['parameters']:
        return False
    if request['error'] != stable_error(record['error']):
        return False
    try:
        result = parse_response(event['response']['text'], Parameters().updated(record['parameters']))
    except (ValueError, TypeError):
        return False
    return result.to_dict() == record['reflection']


def audit_code():
    for path in (ROOT / 'training/refine').glob('*.py'):
        source = path.read_text()
        assert len(source.splitlines()) <= 300, str(path)
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno - node.lineno + 1 <= 50, (path.name, node.name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    directory = OUT / args.run
    manifest = read(directory / 'manifest.json')
    assert manifest['code_sha256'] == fingerprint()
    events = [json.loads(line) for line in (directory / 'requests.jsonl').read_text().splitlines()]
    rows = read(directory / 'result.json')
    assert len(rows) == 18
    totals = {}
    for arm in ('historical_teacher', 'retry', 'teacher'):
        selected = [row for row in rows if row['arm'] == arm]
        assert len(selected) == 6
        totals[arm] = {'success': sum(row['success'] for row in selected), 'tasks': len(selected)}
    for index in manifest['cases']:
        case = f'{index:05d}'
        old = read(COLLECTION / 'tasks' / case / 'result.json')
        for arm in ('retry', 'teacher'):
            result = read(directory / case / arm / 'result.json')
            assert compact(result, case, arm) in rows
            verify_pair(old, result)
            check_result(result, arm, events)
    audit_code()
    result = dict(status='passed', totals=totals, original_results_unchanged=check_originals(),
                  code_and_dataset_hashes_unchanged=True, validation_pairs=12,
                  test_samples_read=0, teacher_requests=len(events),
                  limitation='Small previously audited validation subset; not independent test efficacy')
    (directory / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
