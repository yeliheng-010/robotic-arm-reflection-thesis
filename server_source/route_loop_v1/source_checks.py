import ast,json,hashlib
from pathlib import Path
for name in ('route_loop_v1','noise_feedback_v1'):
    root=Path('/home/yeliheng/grasp_server')/name
    rows=[]
    for path in sorted(root.rglob('*.py')):
        value=path.read_text(); tree=ast.parse(value)
        funcs=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
        row=dict(path=str(path.relative_to(root)),lines=len(value.splitlines()),max_function_lines=max([n.end_lineno-n.lineno+1 for n in funcs] or [0]),max_positional_args=max([len(n.args.args)+len(n.args.posonlyargs)-(1 if n.args.args and n.args.args[0].arg in ('self','cls') else 0) for n in funcs] or [0]))
        assert row['lines']<=300 and row['max_function_lines']<=50 and row['max_positional_args']<=3,row
        rows.append(row)
    (root/'source_checks.json').write_text(json.dumps(dict(passed=True,rows=rows),indent=2))
    protocol=json.loads((root/'protocol.json').read_text())
    evidence=dict(protocol_sha256=hashlib.sha256((root/'protocol.json').read_bytes()).hexdigest(),code=protocol['code'],items=protocol.get('items'),expected=protocol.get('expected',len(protocol.get('items',[]))))
    (root/'protocol_evidence.json').write_text(json.dumps(evidence,indent=2))
    print(name,len(rows),'source checks passed')
