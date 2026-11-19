"""重读输入/接触证据并重建整段路径；拒绝规划不计作搬运成功。"""
import json
import os
from collections import Counter
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import mujoco
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
from manipulator_grasp.arm.robot import UR5e
from stability.kinematics import set_robot_config
from sd_common import read, save, sha
from sd_scene import compiled
from pair_run import audit_sensor
from guard_scope import context as guard_context
from route_policy import eligible
from route_search import choose
from route_inputs import ROOT
from route_prepare import verify


def rebuild(case, trace):
    context = trace['context']
    model, data = compiled(case['config'])
    data.qpos[:] = context['qpos']
    mujoco.mj_forward(model, data)
    robot = UR5e()
    robot._base = sm.SE3(np.array(context['base']))
    robot.robot.base = robot._base
    robot.set_tool(sm.SE3(np.array(context['tool'])))
    robot.set_joint(np.array(context['robot_q']))
    for name, value in zip(('overhead','inline','wrist'), context['config']):
        setattr(robot.robot_config, name, value)
    env = SimpleNamespace(mj_model=model, mj_data=data, joint_names=context['joint_names'])
    return SimpleNamespace(robot=robot, env=env, q0=np.array(context['q0']),
                           q1=np.array(context['q1']), T_wo=sm.SE3(np.array(context['nominal'])))


def reconstruct(case, trace):
    with patch.object(UR5e, 'set_robot_config', set_robot_config), guard_context(case['item'], {}):
        flow = rebuild(case, trace)
        current = choose(flow, item=case['item'], parameters=trace['context']['parameters'],
                         excluded=set(trace['excluded']),
                         hooks=(grasp.move_to_grasp_pose, grasp.move_to_point))
    for name in ('context', 'candidates', 'selected', 'excluded', 'unchanged', 'limitations'):
        assert current[name] == trace[name], name
    return dict(passed=True, candidates=len(trace['candidates']),
                reasons=dict(Counter(r.get('failure', {}).get('reason')
                                     for r in trace['candidates'] if not r['feasible'])))


def attempt(case, step, *, previous, excluded):
    folder = ROOT/'physics'/case['id']/f"attempt_{step['index']}"
    audit = read(folder/'audit.json')
    assert audit['step'] == step
    for name in ('route', 'guard'):
        assert sha(folder/(name+'.json')) == audit[name+'_sha256']
    assert sha(folder/'contacts.jsonl') == audit['trace_sha256']
    assert sha(step['result_path']) == step['result_sha256']
    before = read(case['first']['result_path'])['records'][0]
    record = read(step['result_path'])['records'][0]
    for key in ('initial_qpos', 'initial_body_xyz'):
        np.testing.assert_array_equal(before['candidate_trace'][key], record['candidate_trace'][key])
    assert record['domain_randomization']['level'] == case['config']['group']
    sensor = audit_sensor(record['domain_randomization']['sensor_frames'], case['config'], index=step['index'])
    trace, guard = read(folder/'route.json'), read(folder/'guard.json')
    assert guard['strict_contacts'] and trace['feedback'] == previous['feedback']
    assert trace['active'] == eligible(previous['feedback'], case['item']['destination'])
    rows = [json.loads(line) for line in (folder/'contacts.jsonl').read_text().splitlines()]
    static = None
    if trace['active']:
        assert trace['excluded'] == sorted(excluded)
        assert step['state'] == previous['state']
        assert record['parameters'] == step['state']['parameters']
        static = reconstruct(case, trace)
        selected = trace['selected']
        if selected:
            assert record['approach_plan']['route_id'] == selected['id']
            assert record['approach_plan']['q1'] == selected['q1']
            if record['execution_adapter']:
                assert record['execution_adapter']['lift_height'] == selected['lift']
                np.testing.assert_allclose(selected['pose'], record['execution_adapter']['start'], atol=1e-6, rtol=0)
            excluded.add(selected['id'])
        else:
            assert not step['success'] and not guard['open_called']
            assert step['feedback']['evidence']['route_planning_rejected']
            assert all(r['step'] == 0 for r in rows), 'Rejected planner moved the robot'
    return dict(index=step['index'], success=step['success'], sensor=sensor, static=static,
                selected=(trace.get('selected') or {}).get('id'), guard=guard,
                physics_steps=max(r['step'] for r in rows), result_sha256=step['result_sha256'])


def inspect_case(case):
    assert sha(case['first']['result_path']) == case['first']['result_sha256']
    if case['reused_success']:
        assert case['first']['success'] and case['first']['feedback'] is None
        assert not eligible(None, case['item']['destination'])
        return dict(id=case['id'], success=True, shared=True, new_attempts=0,
                    result_sha256=case['first']['result_sha256'])
    result = read(ROOT/'physics'/case['id']/'result.json')
    steps = result['steps']
    assert steps[0] == case['first'] and 2 <= len(steps) <= 3
    assert [s['index'] for s in steps] == list(range(1, len(steps)+1))
    assert result['success'] == steps[-1]['success']
    assert result['manifest_sha256'] == sha(ROOT/'manifest.json')
    excluded = set()
    rows = [attempt(case, step, previous=steps[i-1], excluded=excluded)
            for i, step in enumerate(steps) if i]
    assert result['excluded'] == sorted(excluded)
    return dict(id=case['id'], success=result['success'], shared=False,
                new_attempts=len(rows), attempts=rows)


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = verify()
    assert read(ROOT/'run_complete.json')['manifest_sha256'] == sha(ROOT/'manifest.json')
    rows = [inspect_case(case) for case in manifest['cases']]
    verify()
    output = dict(passed=True, rows=rows, preserved_successes=sum(r['shared'] for r in rows),
        new_attempts=sum(r['new_attempts'] for r in rows),
        gains=sum(r['success'] and not r['shared'] for r in rows), regressions=0,
        shared_successes_not_rerun=True, promotion_allowed=False, full_48_conditions_rerun=False,
        manifest_sha256=sha(ROOT/'manifest.json'))
    save(ROOT/'verification.json', output)
    print({k:v for k,v in output.items() if k!='rows'}, flush=True)


if __name__ == '__main__':
    main()
