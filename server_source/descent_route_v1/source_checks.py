import ast,json
from pathlib import Path
roots=[Path('/home/yeliheng/grasp_server/descent_pose_v2'),Path('/home/yeliheng/grasp_server/descent_route_v1')]
for root in roots:
    rows=[]
    for path in sorted(root.rglob('*.py')):
        tree=ast.parse(path.read_text())
        funcs=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
        row=dict(path=str(path.relative_to(root)),lines=len(path.read_text().splitlines()),max_function=max([n.end_lineno-n.lineno+1 for n in funcs] or [0]),max_positional=max([len(n.args.args)+len(n.args.posonlyargs)-(1 if n.args.args and n.args.args[0].arg in ('self','cls') else 0) for n in funcs] or [0]))
        assert row['lines']<=300 and row['max_function']<=50 and row['max_positional']<=3,row
        rows.append(row)
    (root/'source_checks.json').write_text(json.dumps(dict(parsed=True,rows=rows),indent=2))
    print(root.name, 'AST and size checks passed',len(rows))
