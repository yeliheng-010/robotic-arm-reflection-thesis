"""冻结前语法、函数长度、位置参数、嵌套与复杂度检查。"""
import ast
from pathlib import Path

BLOCKS = (ast.If,ast.For,ast.While,ast.Try,ast.With)
BRANCHES = (ast.If,ast.For,ast.While,ast.ExceptHandler,ast.IfExp,ast.comprehension)


def depth(node, level=0):
    current = level + isinstance(node,BLOCKS)
    return max([current]+[depth(child,current) for child in ast.iter_child_nodes(node)])


def complexity(node):
    score = 1 + sum(isinstance(n,BRANCHES) for n in ast.walk(node))
    score += sum(len(n.values)-1 for n in ast.walk(node) if isinstance(n,ast.BoolOp))
    return score


def main():
    issues = []
    paths = list(Path(__file__).parent.glob('*.py'))
    for path in paths:
        source = path.read_text()
        tree = ast.parse(source)
        if len(source.splitlines())>300:
            issues.append((path.name,'file_length'))
        functions = [n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
        issues.extend(check(path,functions))
    print(dict(files=len(paths),issues=issues),flush=True)
    assert not issues


def check(path, functions):
    issues = []
    for node in functions:
        values = dict(length=node.end_lineno-node.lineno+1,positional=len(node.args.args),
                      nesting=depth(node),complexity=complexity(node))
        limits = dict(length=50,positional=3,nesting=3,complexity=10)
        for key,value in values.items():
            if value>limits[key]:
                issues.append((path.name,node.name,key,value))
    return issues


if __name__=='__main__':
    main()
