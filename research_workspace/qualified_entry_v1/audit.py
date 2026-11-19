"""独立进程重建原生命令和预测持物资格，不执行物理任务。"""
from unittest.mock import patch
import numpy as np
from qualified_entry_v1.worker import ROOT, PROJECT, RUN, SEED, read, save, sha, inspect, planning
from qualified_entry_v1 import commands, held_preview


def qualify(original, rebuilt):
    for key in ('measurements', 'gate', 'framing', 'calibration', 'accepted', 'geometry_accepted'):
        assert original[key] == rebuilt[key], key
    assert original['rgb']['eligible'] and rebuilt['rgb']['eligible']
    return dict(geometry_identical=True, rgb_eligible_both=True,
        rejected=original['gate']['rejected'], accepted=original['accepted'])


def main():
    manifest = read(RUN/'manifest.json')
    assert all(sha(p) == h for p, h in manifest['identities'].items())
    frozen = {str(p): sha(p) for p in RUN.rglob('*') if p.is_file()}
    folder = RUN/'audit'
    save(folder/'started.json', dict(audit_sha256=sha(ROOT/'audit.py'), identities=frozen))
    source = PROJECT/f'qualified_joint_feedback_v1/run/{SEED}/decision_1'
    record = read(source/'private_plan.json')
    case = read(PROJECT/'qualified_task_v1/run/manifest.json')['cases'][str(SEED)]
    def replay(flow, case, *, geometry, proposal):
        command = commands.run(flow, case, plan=record['plan'], folder=folder)
        assert command == read(RUN/'commands.json')
        forecast = held_preview.inspect(flow, case, plan=record['plan'], folder=folder/'predicted_held')
        assert forecast == read(RUN/'held_preview.json')
        scored = qualify(read(RUN/'predicted_held/qualification.json'),
            read(folder/'predicted_held/qualification.json'))
        with np.load(RUN/'predicted_held/source_state.npz') as old, \
             np.load(folder/'predicted_held/source_state.npz') as new:
            np.testing.assert_array_equal(old['state'], new['state'])
        return dict(commands_identical=True, predicted_state_identical=True, qualification=scored)
    with patch.object(planning, 'run', replay):
        result = inspect(case, read(source/'proposal.json'),
            geometry=read(PROJECT/f'qualified_path_v1/run/goals/{SEED}/geometry.json'))
    assert all(sha(p) == h for p, h in frozen.items())
    assert all(sha(p) == h for p, h in manifest['identities'].items())
    save(RUN/'audit_result.json', dict(result, passed=True, physical_attempts=0,
        model_calls=0, independent_process=True, audit_sha256=sha(ROOT/'audit.py')))
    print(result, flush=True)


if __name__ == '__main__':
    main()
