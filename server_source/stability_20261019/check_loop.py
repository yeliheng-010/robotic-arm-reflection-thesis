import ast,importlib
from pathlib import Path
from stability.experiment import OUT
names=['loop_protocol','loop_freeze','loop_client','loop_service','loop_worker','loop_run','loop_audit']
for name in names:
 path=OUT/'stability'/(name+'.py')
 source=path.read_text()
 assert len(source.splitlines())<=300
 for node in ast.walk(ast.parse(source)):
  if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
   assert node.end_lineno-node.lineno+1<=50,(name,node.name,'function length')
   assert len(node.args.args)+len(node.args.posonlyargs)<=3,(name,node.name,'positional args')
 if name!='loop_service':
  importlib.import_module('stability.'+name)
print('7 files syntax/structure checked; 6 CPU module imports passed')
