"""旧方案零积分回归；历史末态与名义采样分开。"""
from types import SimpleNamespace
from copy import copy
import numpy as np
from qualified_execution_v1.environment import opened, state
from qualified_execution_v1.common import case, plan, RUN as OLD_RUN
from qualified_execution_v1.runtime import native_flow
from qualified_entry_v1.commands import expected
from qualified_execution_v1.contact_audit import restored
from qualified_task_v1.integrity import fingerprint, unchanged
from routecheck.clone import clone_robot
from route_geometry import inspect as robot_check
from qualified_closure_v1.common import RUN, read, save, freeze, verify
from qualified_closure_v1.geometry import sweep, collisions
from qualified_closure_v1.evaluation import record, replay
from qualified_closure_v1.policy import public_feedback

SYNTHETIC_CACHE_OFFSET_M = 1e-4


def commanded_endpoint(env, item):
    selected = plan()
    flow = native_flow(env, selected)
    prefix, _ = expected(flow, selected, parameters=item['state']['parameters'])
    robot = clone_robot(env.robot)
    result = robot_check(robot, env, prefix, item=item['item'])
    assert result['feasible']
    return robot.get_joint().copy(), result


def evaluate_fixtures(env, item):
    quat = read(OLD_RUN / 'physical/initial_quat.json')
    with np.load(OLD_RUN / 'physical/final_state.npz') as values:
        data = restored(env.mj_model, values['state'])
    proxy = SimpleNamespace(mj_model=env.mj_model, mj_data=data)
    baseline = record(proxy, item, initial_quat=quat, folder=RUN / 'restored_terminal',
                      context='historical_terminal_rebuilt_not_original_live_cache')
    assert replay(env.mj_model, RUN / 'restored_terminal')['independent_forward_exact']
    proxy.mj_data = copy(data)
    assert not np.shares_memory(proxy.mj_data.xpos, data.xpos)
    proxy.mj_data.body(item['source']).xpos[0] += SYNTHETIC_CACHE_OFFSET_M
    synthetic = record(proxy, item, initial_quat=quat, folder=RUN / 'synthetic_stale_cache',
                       context='synthetic_cache_offset_test_not_physical_evidence')
    assert not synthetic['cross_timing_identical']
    assert replay(env.mj_model, RUN / 'synthetic_stale_cache')['cached_exact']
    return dict(restored_terminal=baseline, synthetic_stale_cache=synthetic,
                historical_contacts=collisions(env.mj_model, data, item['source']))


def main():
    freeze()
    item = case()
    with opened(item, {}, static=True) as env:
        before = fingerprint(env)
        command, prefix = commanded_endpoint(env, item)
        result = sweep(env, item['item'], command=command)
        save(RUN / 'closure.json', result)
        save(RUN / 'public_feedback.json', public_feedback(result))
        fixtures = evaluate_fixtures(env, item['item'])
        isolation = unchanged(before, fingerprint(env))
    verify()
    summary = dict(closure_passed=result['passed'], prefix=prefix,
                   first_rejected_index=result['first_rejected_index'],
                   valid_linkage_samples=sum(r['valid'] for r in result['rows']),
                   collision_samples=sum(bool(r['contacts']) for r in result['rows']),
                   historical_contacts=fixtures['historical_contacts'], isolation=isolation,
                   physical_attempts=0, model_calls=0, training_runs=0,
                   original_live_terminal_cache_recovered=False)
    save(RUN / 'result.json', summary)
    print(summary, flush=True)


if __name__ == '__main__':
    main()
