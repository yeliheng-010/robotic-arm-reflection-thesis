import hashlib,json
from pathlib import Path
from stability.experiment import OUT
from stability.collection_status import atomic
from stability.parallel_state import validate_plan,lane_indices
from stability.recovery_audit import audit
old,new=OUT/'expert_batch_v1',OUT/'expert_recovery_smoke_v1'
control=OUT/'expert_recovery_smoke_deploy_v1'
result=json.loads((control/'result.json').read_text())
assert result['lane_exit_codes']==[0,0]
checked=audit(new)
assert checked['audited_tasks']==8 and checked['source_audit_passed']
metrics=[json.loads(p.read_text()) for p in (new/'tasks').glob('*/process_*_metrics.json')]
assert len(metrics)==8 and len({m['pid'] for m in metrics})==8
assert all(m['max_rss_kib']<12*1024*1024 for m in metrics)
for i in range(8):
 a=json.loads((old/'tasks'/f'{i:05d}'/'summary.json').read_text())
 b=json.loads((new/'tasks'/f'{i:05d}'/'summary.json').read_text())
 assert a['task']==b['task']
 assert [r['messages'] for r in a['samples']]==[r['messages'] for r in b['samples']]
 for key in ('expert_result','retry_result'):
  x,y=[json.loads(Path(s[key]).read_text()) for s in (a,b)]
  assert x['success']==y['success'] and x['attempts']==y['attempts']
  for xr,yr in zip(x['records'],y['records']):
   assert all(xr[k]==yr[k] for k in ('parameters','accepted','physical_success'))
   assert (xr['error'] or {}).get('error_type')==(yr['error'] or {}).get('error_type')
complete=validate_plan(new,5700)
assert all(lane_indices(8,lane=i,lanes=2,completed=complete)==[] for i in range(2))
report=dict(passed=True,completed_tasks=8,unique_processes=8,max_task_rss_kib=max(m['max_rss_kib'] for m in metrics),no_completed_task_resubmission=True,physical_and_supervision_parity=True,metrics=metrics)
atomic(control/'verification.json',report)
archive=old/'status_before_recovery_3713.json'
assert json.loads(archive.read_text())==json.loads((old/'status.json').read_text())
admission=dict(old_status_path=str(archive),old_status_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),old_failure='slurm_step_memory_limit_12G',mitigation='fresh_process_per_task_and_24G_per_lane',smoke_root=str(new),smoke_control=str(control),caveat='Memory growth site not localized; process exit bounds lifetime; long run still requires monitoring')
atomic(OUT/'expert_recovery_batch_deploy_v1'/'recovery_admission.json',admission)
print(json.dumps({k:report[k] for k in report if k!='metrics'}))
