"""物理对照及旧数据核验，不把点云通过等同于动作成功。"""
import argparse
import ast
import json
from collections import Counter
from geometry.verify import compare_pair, check_result
from stability.experiment import OUT, fingerprint
from training.refine.verify import check_originals


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    directory = OUT/parser.parse_args().run
    configuration = read(directory/'manifest.json')
    assert configuration['fingerprint'] == fingerprint()
    rows = read(directory/'result.json')
    assert len(rows) == 2*len(configuration['tasks'])
    unchanged = 0
    for index, task in enumerate(configuration['tasks']):
        results = []
        for arm in configuration['arms']:
            result = read(directory/f'{index:02d}'/arm/'result.json')
            check_result(result, task=task, arm='multi')
            assert all(r['stable_voxel_grid'] == (arm == 'stable') for r in result['records'])
            results.append(result)
        unchanged += compare_pair(results)
    for path in (OUT/'stability').glob('*.py'):
        source = path.read_text()
        assert len(source.splitlines()) <= 300, path.name
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno-node.lineno+1 <= 50, (path.name, node.name)
    statistics = {}
    for arm in configuration['arms']:
        selected = [r for r in rows if r['arm'] == arm]
        statistics[arm] = {'success': sum(r['success'] for r in selected), 'tasks': len(selected),
            'none_success': sum(r['success'] for r in selected if r['fault'] == 'none'),
            'none_tasks': sum(r['fault'] == 'none' for r in selected),
            'last_errors': dict(Counter(r['last_error'] for r in selected))}
    report = {'status': 'passed', 'statistics': statistics, 'pairs': len(configuration['tasks']),
        'unchanged_first_grasp_pairs': unchanged, 'original_records_unchanged': check_originals()}
    (directory/'verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
