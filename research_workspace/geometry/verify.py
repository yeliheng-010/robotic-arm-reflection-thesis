"""结果来源、初始状态配对、代码冻结及旧文件指纹核验。"""
import argparse
import ast
from collections import Counter
import json
import numpy as np
from reflection.reflector import Parameters
from training.refine.verify import check_originals
from geometry.experiment import OUT, compact, fingerprints


def read(path):
    return json.loads(path.read_text())


def check_record(record, *, arm):
    trace = record['candidate_trace']
    assert trace['arm'] == arm
    assert trace['source'] == 'geometric_candidates_with_rule_reflection'
    filtering = record['diagnostics'].get('grasp_filter')
    if filtering:
        assert filtering['collision_threshold'] == .01
    for row in trace.get('returned', []):
        assert any(np.allclose(row, raw, atol=1e-12, rtol=0) for raw in trace['generated'])
    if record['accepted']:
        assert record['physical_success'] and record['error'] is None
    assert 'reflection_error' not in record


def check_result(result, *, task, arm):
    for key, value in task.items():
        assert result[key] == value
    assert result['reflector'] == 'RuleReflector'
    records = result['records']
    assert result['attempts'] == len(records) <= 3
    assert result['success'] == any(r['accepted'] for r in records)
    for index, record in enumerate(records):
        check_record(record, arm=arm)
        if 'reflection' in record:
            answer = record['reflection']
            assert answer['source'] == 'rule'
            updated = Parameters().updated(record['parameters']).updated(answer['changes']).to_dict()
            assert json.loads(json.dumps(updated)) == records[index+1]['parameters']


def compare_pair(results):
    first = [r['records'][0] for r in results]
    traces = [r['candidate_trace'] for r in first]
    for field in ('initial_qpos', 'initial_body_xyz'):
        np.testing.assert_allclose(traces[0][field], traces[1][field], atol=1e-8, rtol=0)
    assert first[0]['parameters'] == first[1]['parameters']
    selected = [t.get('returned', [])[:1] for t in traces]
    unchanged = bool(selected[0] and selected[1] and np.allclose(selected[0], selected[1], atol=1e-12, rtol=0))
    if unchanged:
        for field in ('physical_success', 'accepted'):
            assert first[0][field] == first[1][field]
        np.testing.assert_allclose(first[0]['evaluation']['position'], first[1]['evaluation']['position'],
                                   atol=1e-8, rtol=0)
    return unchanged


def audit_code():
    for path in (OUT / 'geometry').glob('*.py'):
        source = path.read_text()
        assert len(source.splitlines()) <= 300, path.name
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno-node.lineno+1 <= 50, (path.name, node.name)


def statistics(rows, arm):
    selected = [r for r in rows if r['arm'] == arm]
    return {'tasks': len(selected), 'success': sum(r['success'] for r in selected),
            'first_success': sum(r['first_success'] for r in selected),
            'recoveries': sum(r['success'] and not r['first_success'] for r in selected),
            'attempts': sum(r['attempts'] for r in selected),
            'first_errors': dict(Counter(r['first_error'] for r in selected)),
            'last_errors': dict(Counter(r['last_error'] for r in selected))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    directory = OUT / parser.parse_args().run
    config, rows = read(directory/'manifest.json'), read(directory/'result.json')
    assert config['code_sha256'] == fingerprints()
    assert config['threads'] == read(directory/'runtime.json')['threads']
    assert len(rows) == len(config['tasks'])*len(config['arms'])
    unchanged = 0
    for index, task in enumerate(config['tasks']):
        results = []
        for arm in config['arms']:
            result = read(directory/f'{index:02d}'/arm/'result.json')
            check_result(result, task=task, arm=arm)
            assert dict(compact(result, arm=arm), case=index) in rows
            results.append(result)
        unchanged += compare_pair(results)
    audit_code()
    report = {'status': 'passed', 'initial_state_pairs': len(config['tasks']),
              'unchanged_first_grasp_physics_pairs': unchanged,
              'original_records_unchanged': check_originals(), 'test_samples_read': 0,
              'statistics': {arm: statistics(rows, arm) for arm in config['arms']}}
    (directory/'verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
