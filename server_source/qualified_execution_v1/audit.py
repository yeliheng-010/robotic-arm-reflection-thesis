"""独立重建每段安全检查和最终物理验收，不重跑真实动作。"""
import numpy as np
import mujoco
import spatialmath as sm
from qualified_execution_v1.environment import opened
from qualified_execution_v1.common import ROOT, RUN, read, save, sha, verify, case, plan
from qualified_execution_v1.policy import accepted
from audit_motion_live import rebuild, RecordedPlanner
from route_geometry import inspect as robot_check
from hv_geometry import inspect as held_check
from reflection.monitors import evaluate_placement


def paths(item, records):
    rows = []
    pose = sm.SE3(np.asarray(plan()['selected']['pose']))
    for row in records:
        robot, env = rebuild(item, row['context'])
        segments = [(r['phase'], RecordedPlanner(r), r['duration']) for r in row['legs']]
        if row['phase'] == 'carry':
            result = held_check(robot, env, segments, item=item['item'], grasp=pose)
        else:
            result = robot_check(robot, env, segments, item=item['item'])
        assert result == row['result']
        assert row['executed'] == result['feasible']
        if row['executed']:
            assert row['end_time'] >= row['start_time']
        rows.append(dict(phase=row['phase'], feasible=result['feasible'], executed=row['executed']))
    return rows


def main():
    verify()
    folder, item = RUN/'physical', case()
    frozen = {str(p): sha(p) for p in folder.rglob('*') if p.is_file()}
    recorded = read(folder/'result.json')
    assert read(RUN/'attempt_claim.json')['consumed'] == 1
    with opened(item, {}, static=True) as env:
        rebuilt_paths = paths(item, read(folder/'private_paths.json'))
        with np.load(folder/'final_state.npz') as values:
            mujoco.mj_setState(env.mj_model, env.mj_data, values['state'], mujoco.mjtState.mjSTATE_INTEGRATION)
        mujoco.mj_forward(env.mj_model, env.mj_data)
        physical, evaluation, _ = evaluate_placement(env, item['item']['source'], item['item']['destination'],
            np.asarray(read(folder/'initial_quat.json')))
        assert bool(physical) == recorded['physical_placement'] and evaluation == recorded['evaluation']
    success = accepted(completed=recorded['completed'], physical_placement=bool(physical),
        safety_error=recorded['safety_error'])
    assert success == recorded['success']
    assert not read(folder/'publication.json')['model_input_published']
    assert all(sha(p) == h for p, h in frozen.items())
    verify()
    result = dict(passed=True, independent=True, paths=rebuilt_paths, final_evaluation_identical=True,
        success=success, actual_physical_attempts=1, audit_physical_attempts=0, model_calls=0,
        identities=frozen, source_sha256=sha(ROOT/'audit.py'))
    save(RUN/'physical_audit.json', result)
    print({k: v for k, v in result.items() if k != 'identities'}, flush=True)


if __name__ == '__main__':
    main()
