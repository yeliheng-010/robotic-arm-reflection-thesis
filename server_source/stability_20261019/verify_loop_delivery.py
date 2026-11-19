import ast,json
from stability.experiment import OUT
from stability.loop_freeze import ROOT,verify
from stability.loop_audit import audit
from stability.sft_freeze import file_hash
from stability.collection_status import atomic
result=json.loads((ROOT/'result.json').read_text())
assert result['status']=='completed'
config=verify()
verification=audit(config,result['rows'])
record=json.loads((ROOT/'completion_recovery.json').read_text())
assert all(file_hash(ROOT/p)==h for p,h in record['raw_files_unchanged'].items())
for name in ('loop_results.py','loop_finalize.py','loop_report.py'):
 source=(OUT/'stability'/name).read_text()
 assert len(source.splitlines())<=300
 for node in ast.walk(ast.parse(source)):
  if isinstance(node,ast.FunctionDef):
   assert node.end_lineno-node.lineno+1<=50,(name,node.name)
   assert len(node.args.args)+len(node.args.posonlyargs)<=3,(name,node.name)
delivery=dict(passed=True,verification=verification,raw_hashes_unchanged=True,
 trained_adapter_unchanged=True,metadata_recovery_record=str(ROOT/'completion_recovery.json'))
atomic(ROOT/'delivery_verification.json',delivery)
print(json.dumps(delivery))
