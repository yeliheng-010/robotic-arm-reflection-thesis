"""核对本轮源码规模、参数数目与分支复杂度；不改冻结文件。"""
import ast
import json
from pathlib import Path
from cc_common import sha

BASE=Path(__file__).resolve().parents[2]
FOLDERS=('joint_policy_v1','joint_policy_v2','observed_yaw_v1','observed_long_v1')


def complexity(node):
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):
        return 0
    own=int(isinstance(node,(ast.If,ast.For,ast.While,ast.ExceptHandler,ast.IfExp,ast.comprehension)))
    if isinstance(node,ast.BoolOp):
        own += len(node.values)-1
    return own+sum(complexity(child) for child in ast.iter_child_nodes(node))


def main():
    rows=[]
    for folder in FOLDERS:
        for path in (BASE/folder).rglob('*.py'):
            if 'evidence' in path.parts:
                continue
            source=path.read_text()
            assert len(source.splitlines())<=300,path
            tree=ast.parse(source)
            functions=[]
            for node in ast.walk(tree):
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    score=1+sum(complexity(child) for child in node.body)
                    assert score<=10,(path,node.name,score)
                    assert node.end_lineno-node.lineno+1<=50,(path,node.name)
                    assert len(node.args.posonlyargs+node.args.args)<=3,(path,node.name)
                    functions.append(dict(name=node.name,complexity=score))
            rows.append(dict(path=str(path),sha256=sha(path),functions=functions))
    output=Path(__file__).with_name('source_check.json')
    with output.open('x') as stream:
        json.dump(dict(passed=True,files=rows),stream,indent=2)
    print(dict(passed=True,files=len(rows)),flush=True)


if __name__ == '__main__':
    main()
