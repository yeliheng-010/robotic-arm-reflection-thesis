"""恢复前核对旧故障归档和新调度器真实smoke证据。"""
import hashlib
import json
from pathlib import Path


def check_admission(root, control, old_status):
    if not old_status.get('worker_failures'):
        return None
    record = json.loads((control/'recovery_admission.json').read_text())
    archived = Path(record['old_status_path'])
    assert hashlib.sha256(archived.read_bytes()).hexdigest() == record['old_status_sha256']
    assert json.loads(archived.read_text()) == old_status
    assert record['old_failure'] == 'slurm_step_memory_limit_12G'
    assert record['mitigation'] == 'fresh_process_per_task_and_24G_per_lane'
    smoke = Path(record['smoke_control'])
    result = json.loads((smoke/'result.json').read_text())
    audit = json.loads((Path(record['smoke_root'])/'recovery_audit.json').read_text())
    assert result['lane_exit_codes'] == [0, 0] and not result['status']['worker_failures']
    assert audit['source_audit_passed'] and audit['audited_tasks'] >= 8
    current = json.loads((control/'manifest.json').read_text())
    tested = json.loads((smoke/'manifest.json').read_text())
    assert current['scheduler_code'] == tested['scheduler_code']
    assert (root/'manifest.json').read_bytes() == (Path(record['smoke_root'])/'manifest.json').read_bytes()
    return str(control/'recovery_admission.json')
