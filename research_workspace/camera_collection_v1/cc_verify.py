"""启动前验证所有入口可导入、来源正确及局部代码长度。"""
import ast
import importlib
from cc_common import ROOT


def main():
    checked = []
    for path in sorted(ROOT.glob('*.py')):
        source = path.read_text(encoding='utf-8')
        tree = ast.parse(source, filename=str(path))
        assert len(source.splitlines()) <= 300, path
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno-node.lineno+1 <= 50, (path, node.name)
        module = importlib.import_module(path.stem)
        assert module.__file__ == str(path)
        checked.append(path.name)
    import audit
    import common
    assert '/ai_safe_visual_loop_v1/' in audit.__file__, audit.__file__
    assert '/natural_top_preflight_v1/' in common.__file__, common.__file__
    print(dict(passed=True, entries=checked, audit=audit.__file__, common=common.__file__), flush=True)


if __name__ == '__main__':
    main()
