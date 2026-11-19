"""检查新目录源码规模、语法、依赖冻结和结果账本。"""
import ast
from pathlib import Path
import importlib.util
from cc_common import read,save,sha,verify

ROOT=Path(__file__).resolve().parent


def complexity(node):
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):
        return 0
    own=int(isinstance(node,(ast.If,ast.For,ast.While,ast.ExceptHandler,ast.IfExp,ast.comprehension)))
    if isinstance(node,ast.BoolOp):
        own+=len(node.values)-1
    return own+sum(complexity(child) for child in ast.iter_child_nodes(node))


def inspect(path):
    source=path.read_text()
    assert len(source.splitlines())<=300,path
    tree=ast.parse(source)
    compile(tree,str(path),'exec')
    functions=[]
    for node in ast.walk(tree):
        if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            continue
        score=1+sum(complexity(child) for child in node.body)
        assert score<=10,(path,node.name,score)
        assert node.end_lineno-node.lineno+1<=50,(path,node.name)
        assert len(node.args.posonlyargs+node.args.args)<=3,(path,node.name)
        functions.append(dict(name=node.name,complexity=score))
    return dict(path=str(path),sha256=sha(path),functions=functions)


def main():
    files=[inspect(p) for p in ROOT.rglob('*.py') if 'evidence' not in p.parts]
    paths=[ROOT/'endpoints/manifest.json',ROOT/'endpoints_v2/manifest.json',ROOT/'tilt/results/manifest.json']
    for path in paths:
        verify(path)
    assert verify(ROOT/'endpoints_v2/result.json')['passed']
    assert verify(ROOT/'tilt/results/result.json')['passed']
    identities={str(p):sha(p) for p in ROOT.rglob('*') if p.suffix in ('.py','.sh','.sbatch') and 'evidence' not in p.parts}
    save(ROOT/'source_review.json',dict(passed=True,files=files,identities=identities,
        physical_attempts=0,model_calls=0,scope='syntax_function_size_arguments_branch_complexity_and_frozen_inputs'))
    print(dict(passed=True,python_files=len(files),source_files=len(identities)),flush=True)


if __name__=='__main__':
    main()
