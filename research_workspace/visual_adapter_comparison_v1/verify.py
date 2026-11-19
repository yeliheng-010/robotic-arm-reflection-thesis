"""独立进程入口验证及源冻结，不加载模型、不生成。"""
import ast
import os
import subprocess
import sys
from pathlib import Path
from ac_common import common

MODULES = ('ac_prepare', 'ac_run', 'ac_report')
MAX_FILE_LINES = 300
MAX_FUNCTION_LINES = 50


def main():
    assert os.environ.get('SLURM_JOB_ID')
    root = Path(__file__).resolve().parent
    for module in MODULES:
        source = (f'import {module} as m; from pathlib import Path; '
            f'assert Path(m.__file__).resolve() == Path({str(root / (module+".py"))!r}); '
            'print(m.__file__)')
        subprocess.run([sys.executable, '-B', '-c', source], cwd=root, check=True)
    for path in root.glob('*.py'):
        source = path.read_text(encoding='utf-8')
        assert len(source.splitlines()) <= MAX_FILE_LINES
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno - node.lineno + 1 <= MAX_FUNCTION_LINES
    paths = [*root.glob('*.py'), *root.glob('*.sbatch'), root / 'PLAN.md']
    common.save(root / 'source_manifest.json', dict(identities={str(p): common.sha(p) for p in paths},
        model_loads=0, model_generations=0, training_updates=0, physical_attempts=0))
    print('Isolated actual entry paths verified; sources frozen; no model load or generation')


if __name__ == '__main__':
    main()
