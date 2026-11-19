import ast,json,pathlib
root=pathlib.Path('/home/yeliheng/grasp_server/stability_20261019/stability')
files=list(root.glob('sft_*.py'))+[root/'pilot_release.py',root/'test_sft_data.py']
issues=[(p.name,n.name,n.end_lineno-n.lineno+1,len(n.args.posonlyargs)+len(n.args.args)) for p in files for n in ast.walk(ast.parse(p.read_text())) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and (n.end_lineno-n.lineno+1>50 or len(n.args.posonlyargs)+len(n.args.args)>3)]
result={'files':len(files),'issues':issues,'oversize':[p.name for p in files if len(p.read_text().splitlines())>300]}
print(json.dumps(result));assert not issues and not result['oversize']
