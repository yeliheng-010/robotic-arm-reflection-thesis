"""核验新增入口、函数长度与实际导入的旧审计模块。"""
import ast
import importlib
from ta_common import ROOT


def main():
    names = []
    for path in sorted(ROOT.glob('*.py')):
        source = path.read_text(encoding='utf-8')
        tree = ast.parse(source)
        assert len(source.splitlines()) <= 300
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno-node.lineno+1 <= 50, (path.name, node.name)
        module = importlib.import_module(path.stem)
        assert module.__file__ == str(path)
        names.append(path.name)
    import audit
    assert '/ai_safe_visual_loop_v1/' in audit.__file__
    print(dict(passed=True, entries=names, audit=audit.__file__), flush=True)


if __name__ == '__main__':
    main()
