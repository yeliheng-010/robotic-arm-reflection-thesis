"""只导入真实入口和检查源结构，然后冻结本目录；不加载模型。"""
import ast
import os
from pathlib import Path
import review

MAX_FUNCTION_LINES = 50
MAX_FILE_LINES = 300


def main():
    assert os.environ.get('SLURM_JOB_ID')
    root = Path(__file__).resolve().parent
    assert Path(review.__file__).resolve() == root / 'review.py'
    paths = [*root.glob('*.py'), *root.glob('*.sbatch'), root / 'PLAN.md']
    for path in root.glob('*.py'):
        source = path.read_text(encoding='utf-8')
        assert len(source.splitlines()) <= MAX_FILE_LINES
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno - node.lineno + 1 <= MAX_FUNCTION_LINES
    review.common.save(root / 'source_manifest.json', dict(
        identities={str(p): review.common.sha(p) for p in paths},
        model_loads=0, training_updates=0, physical_attempts=0))
    print('Actual v2 imports and source bounds passed; no model load/update; source frozen')


if __name__ == '__main__':
    main()
