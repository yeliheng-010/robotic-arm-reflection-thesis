import ast,json
from pathlib import Path
root=Path('/home/yeliheng/grasp_server/feedback_semantics_v2')
rows=[]
for p in sorted(root.rglob('*.py')):
    text=p.read_text(); tree=ast.parse(text)
    functions=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
    rows.append(dict(path=str(p.relative_to(root)),lines=len(text.splitlines()),max_function_lines=max([n.end_lineno-n.lineno+1 for n in functions] or [0]),max_positional_args=max([len(n.args.posonlyargs)+len(n.args.args)-(1 if n.args.args and n.args.args[0].arg in ('self','cls') else 0) for n in functions] or [0])))
result=dict(parsed=True,rows=rows)
(root/'analysis/source_checks.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
