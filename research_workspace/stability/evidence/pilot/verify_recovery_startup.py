import json
from stability.experiment import OUT
from stability.recovery_audit import audit_recovered_task
from stability.parallel_state import verify_identity
from stability.collection_status import atomic
root,control=OUT/'expert_batch_v1',OUT/'expert_recovery_batch_deploy_v1'
verify_identity(root,control)
manifest=json.loads((root/'manifest.json').read_text())
lanes=[json.loads((control/f'lane_{i}.json').read_text()) for i in range(2)]
assert all(lane['completed'] and not lane['errors'] for lane in lanes)
cases=sorted({i for lane in lanes for i in lane['completed']})
counts=[audit_recovered_task(root/'tasks'/f'{i:05d}',manifest['plan'][i])[0] for i in cases]
assert 372 in cases and 374 in cases
result=dict(passed=True,job='3715',lanes=2,workers_per_lane=2,new_completed_tasks=cases,
 audited_new_samples=sum(counts),recovered_partial_tasks=[372,374],errors=[],batch_not_complete=True)
atomic(control/'startup_verification.json',result)
print(json.dumps(result))
