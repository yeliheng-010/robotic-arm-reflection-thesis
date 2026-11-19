"""保留迁移前证据并归档本次调度切换的STOP标记。"""
import fcntl
import hashlib
import json
from pathlib import Path
from stability.experiment import OUT
from stability.expert_audit import audit
from stability.collection_status import atomic

root = OUT/'expert_batch_v1'
with (root/'.collector.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    result = audit(root)
    assert result['source_audit_passed'] and not result['status'].get('worker_failures')
    files = list((root/'tasks').rglob('result.json'))+list((root/'tasks').glob('*/summary.json'))
    snapshot = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    target = root/'migration_parallel_before.json'
    assert not target.exists()
    atomic(target, {'files': snapshot, 'status': result['status']})
    stop = root/'STOP'
    archived = root/'STOP.migration_parallel_archived'
    assert 'Controlled migration to independent GPU lanes' in stop.read_text()
    assert not archived.exists()
    stop.rename(archived)
    print(json.dumps({'preserved_files': len(snapshot), 'completed_tasks': result['audited_tasks']}))
