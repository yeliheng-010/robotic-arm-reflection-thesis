"""验证当前入口源码；保留并显式列出已替代的冻结复杂函数。"""
import ast
from pathlib import Path
from source_review import complexity
from cc_common import save,sha,verify,read

ROOT=Path(__file__).resolve().parent
ARCHIVED={('path/hp_geometry.py','inspect'),('path/hp_search.py','explore')}


def depth(node):
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):
        return 0
    own=int(isinstance(node,(ast.If,ast.For,ast.While,ast.With,ast.Try)))
    return own+max((depth(child) for child in ast.iter_child_nodes(node)),default=0)


def functions(path, tree):
    rows=[]
    relative=path.relative_to(ROOT).as_posix()
    for node in ast.walk(tree):
        if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            continue
        values=dict(name=node.name,lines=node.end_lineno-node.lineno+1,
            positional=len(node.args.posonlyargs+node.args.args),
            complexity=1+sum(complexity(child) for child in node.body),
            nesting=max((depth(child) for child in node.body),default=0))
        passed=values['lines']<=50 and values['positional']<=3 and values['complexity']<=10 and values['nesting']<=3
        archived=(relative,node.name) in ARCHIVED
        assert passed or archived,(relative,values)
        rows.append(dict(values,passed=passed,archived=archived))
    return rows


def main():
    files=[]
    for path in ROOT.rglob('*.py'):
        if 'evidence' in path.parts:
            continue
        source=path.read_text()
        assert len(source.splitlines())<=300,path
        tree=ast.parse(source)
        compile(tree,str(path),'exec')
        files.append(dict(path=str(path),sha256=sha(path),functions=functions(path,tree)))
    paths=[ROOT/'path_v2/results/manifest.json',ROOT/'trial_gpu_v2/manifest.json']
    for path in paths:
        verify(path)
    assert read(ROOT/'trial_gpu_v2/preflight_result.json')['passed']
    identities={str(p):sha(p) for p in ROOT.rglob('*') if p.suffix in ('.py','.sh','.sbatch') and 'evidence' not in p.parts}
    save(ROOT/'final_review.json',dict(passed=True,files=files,identities=identities,
        archived_functions=[list(v) for v in sorted(ARCHIVED)]))
    print(dict(passed=True,python_files=len(files),source_files=len(identities)),flush=True)


if __name__=='__main__':
    main()
