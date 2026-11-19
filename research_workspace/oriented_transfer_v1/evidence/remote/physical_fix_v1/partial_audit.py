"""只读核验已消费尝试的部分证据；不伪造缺失的任务结果。"""
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import op_common
from cc_common import read, save, sha, verify
from op_audit import live_check
from op_choose import pair
from sr_audit import measured

ROOT = Path(__file__).resolve().parent
TRIAL = ROOT.parent/'trial_gpu_v2'
FOLDER = TRIAL/'cases/964345/first'


def sources():
    paths = [p for p in FOLDER.rglob('*') if p.is_file()]
    paths += [TRIAL/'manifest.json', ROOT.parent/'physical/execute-v2-6461.log']
    return {str(p): sha(p) for p in paths}


def actions():
    bridge = read(FOLDER/'bridge.json')
    planners = bridge['planners']
    assert len(planners) == 3
    assert all(p['action'] == 'move_to_grasp_pose' and p['executed'] for p in planners)
    rows = read(FOLDER/'telemetry.json')['rows']
    counts = dict(Counter(r['action'] for r in rows))
    assert set(counts) == {'idle', 'move_to_grasp_pose', 'close_gripper'}
    assert rows[-1]['action'] == 'close_gripper'
    guard = read(FOLDER/'guard.json')
    assert not guard['release_checked'] and not guard['open_called']
    return dict(planners=[{k: p[k] for k in ('action', 'executed', 'start_time', 'end_time')}
        for p in planners], telemetry_samples=len(rows), telemetry_actions=counts,
        last_time_s=rows[-1]['time_s'], last_action=rows[-1]['action'],
        carry_planner_entered=False, release_entered=False, guard=guard)


def lifecycle():
    value = read(FOLDER/'lifecycle.json')
    assert value['released'] and value['actual_close_calls'] == 1
    assert value['exit_exception'] == 'FileExistsError'
    absent = [FOLDER/'step.json', FOLDER/'execution/result.json', FOLDER.parent/'result.json',
        TRIAL/'audit.json']
    assert all(not p.exists() for p in absent)
    log = (ROOT.parent/'physical/execute-v2-6461.log').read_text()
    assert 'FileExistsError' in log and 'live_held_check.json' in log
    return dict(state=value, missing=[str(p) for p in absent])


def main():
    before = sources()
    manifest = verify(TRIAL/'manifest.json')
    case = manifest['entry']['case']
    assert read(FOLDER/'approved_plan_match.json')['actual_plan_identical']
    assert read(FOLDER/'initial_visibility.json')['accepted']
    with patch.object(op_common, 'TRIAL', TRIAL):
        inputs = pair(FOLDER)
    contact = measured(FOLDER)
    closing = contact.pop('closing_end')
    contact['closing_observed'] = closing is not None
    contact['private_note'] = 'Contact evidence is not proof of stable lifting or full-task safety.'
    output = dict(audit_completed=True, status='partial_execution_software_failure',
        task_success=None, new_verified_successes=0, physical_attempts_consumed=1,
        model_calls=0, training_updates=0, actions=actions(), lifecycle=lifecycle(),
        inputs=inputs, contacts=contact, live_guard_recomputed=live_check(case, FOLDER),
        limit='No completed carry, release, return or task-result evidence; no task-success audit.',
        identities=before)
    assert before == sources(), 'Original evidence changed during read-only audit'
    verify(TRIAL/'manifest.json')
    save(ROOT/'partial_audit.json', output)
    print({k: output[k] for k in ('audit_completed', 'status', 'physical_attempts_consumed')})


if __name__ == '__main__':
    main()
