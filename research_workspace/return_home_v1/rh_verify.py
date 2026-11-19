"""启动前导入和长度核验，不执行物理动作。"""
import ast
import importlib
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    names = []
    for path in sorted(root.glob('*.py')):
        code = path.read_text(encoding='utf-8')
        tree = ast.parse(code)
        assert len(code.splitlines()) <= 300
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno-node.lineno+1 <= 50, (path.name, node.name)
        assert importlib.import_module(path.stem).__file__ == str(path)
        names.append(path.name)
    print(dict(passed=True, entries=names), flush=True)


if __name__ == '__main__':
    main()
