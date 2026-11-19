"""正式恢复后核对旧数据原件、代码身份、单写入锁和GPU分片。"""
import fcntl
import hashlib
import json
from stability.experiment import OUT
from stability.expert_config import configuration
from stability.parallel_state import verify_identity

root = OUT/'expert_batch_v1'
control = OUT/'expert_parallel_batch_deploy_v1'
snapshot = json.loads((root/'migration_parallel_before.json').read_text())
for name, expected in snapshot['files'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest() == expected, name
assert json.loads((root/'manifest.json').read_text()) == configuration('batch')
verify_identity(root, control)
held = False
with (root/'.collector.lock').open('a') as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        held = True
assert held, 'Collector is not holding its exclusive lock'
lanes = [json.loads((control/f'lane_{i}.json').read_text()) for i in range(2)]
assert all(not lane['errors'] for lane in lanes)
result = {'preserved_files': len(snapshot['files']), 'unchanged': True, 'identity_matches': True,
          'collector_lock_held': held, 'lanes': lanes}
(control/'startup_verification.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
