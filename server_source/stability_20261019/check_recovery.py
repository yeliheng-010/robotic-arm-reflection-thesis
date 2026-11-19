import ast,json
from pathlib import Path
from stability.experiment import OUT
from stability.recovery_audit import audit
from stability.collection_status import atomic
result=audit(OUT/'expert_batch_v1')
print(json.dumps({k:result[k] for k in ('source_audit_passed','audited_tasks','raw_verified_samples','verified_early_aborts_without_samples')}))
names=['recovery_audit.py','recovery_review.py','recovery_task.py','parallel_lane.py','parallel_collect.py','parallel_state.py','sft_validate.py']
for name in names:
 p=OUT/'stability'/name
 source=p.read_text()
 assert len(source.splitlines())<=300,(name,'file length')
 for node in ast.walk(ast.parse(source)):
  if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
   assert node.end_lineno-node.lineno+1<=50,(name,node.name,'function length')
   assert len(node.args.posonlyargs)+len(node.args.args)<=3,(name,node.name,'arguments')
print('Structure checks passed for',len(names),'files')
trained=json.loads((OUT/'pilot_sft_v1/result.json').read_text())
order=json.loads((OUT/'pilot_sft_v1/epoch_order.json').read_text())
assert trained['status']=='completed'
assert len(trained['updates'])==21 and sum(u['samples'] for u in trained['updates'])==163
assert sorted(sum(order,[]))==list(range(163))
assert trained['changed_adapter_tensors']>0 and trained['adapter_reload_max_logit_error']==0
assert trained['test_used'] is False
atomic(OUT/'pilot_sft_v1/completion_verification.json',dict(passed=True,optimizer_steps=21,unique_training_samples=163,adapter_reload_error=0,test_used=False))
print('Training completion checks passed')
