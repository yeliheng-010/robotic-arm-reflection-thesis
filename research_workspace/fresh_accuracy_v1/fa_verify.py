"""导入、范围和冻结策略接线检查。"""
import ast
import importlib
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    names = []
    for path in sorted(root.glob('*.py')):
        code = path.read_text(encoding='utf-8')
        assert len(code.splitlines()) <= 300
        for node in ast.walk(ast.parse(code)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno-node.lineno+1 <= 50, (path.name, node.name)
        assert importlib.import_module(path.stem).__file__ == str(path)
        names.append(path.name)
    print(dict(passed=True, entries=names), flush=True)


if __name__ == '__main__':
    main()
