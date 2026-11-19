"""原六项回归及真实首批逐字段等价，不重复物理/模型执行。"""
import ast
import os
import unittest
from pathlib import Path
import coverage_stats as old
import coverage_stats_v2 as new
import test_coverage as tests
from report import load_source, load_cases

ROOT = Path(__file__).resolve().parent
MAX_COMPLEXITY = 10
MAX_FUNCTION_LINES = 50


def branch_score(node):
    score = 1
    for item in ast.walk(node):
        if isinstance(item, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.IfExp)):
            score += 1
        elif isinstance(item, ast.BoolOp):
            score += len(item.values) - 1
        elif isinstance(item, ast.comprehension):
            score += 1 + len(item.ifs)
    return score


def main():
    assert os.environ.get('SLURM_JOB_ID')
    tests.coverage, tests.task_counts = new.coverage, new.task_counts
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
    assert result.wasSuccessful()
    manifest, rows, identities = load_source()
    cases, qualified = load_cases(manifest['batches'], identities)
    assert old.stages(cases, qualified, rows) == new.stages(cases, qualified, rows)
    assert old.task_counts(rows) == new.task_counts(rows)
    tree = ast.parse((ROOT/'coverage_stats_v2.py').read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            assert node.end_lineno - node.lineno + 1 <= MAX_FUNCTION_LINES
            assert branch_score(node) <= MAX_COMPLEXITY, node.name
    print('Real exported stages and task counts exactly equal; bounded function sizes/branches; zero physics/model/update')


if __name__ == '__main__':
    main()
