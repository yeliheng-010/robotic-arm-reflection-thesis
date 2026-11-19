"""完整路径之后检查闭合及原生命令；只返回公开阶段反馈。"""
from types import SimpleNamespace
from model_grasp_intent_v1.geometry import propose
from qualified_path_v1.worker import inspect
from qualified_joint_feedback_v1.policy import outcome
from qualified_execution_v1.environment import opened
from qualified_execution_v1.runtime import native_flow
from qualified_entry_v1.commands import expected, run as native_commands
from qualified_task_v1.observer import observe, ObservationRejected
from qualified_task_v1.integrity import fingerprint, unchanged
from qualified_closure_v2.geometry import sweep
from routecheck.clone import clone_robot
from route_geometry import inspect as robot_check
from qualified_closure_feedback_v1.common import PROJECT, SEED, read, save
from qualified_closure_feedback_v1.policy import permitted


def extra(case, plan, folder):
    row = plan['selected']
    if row['approach_route'] != 'direct' or row['transport_route'] != 'direct' or row.get('joint_option'):
        return dict(status='rejected', stage='execution_entry')
    with opened(case, {}, static=True) as env:
        before = fingerprint(env)
        flow = native_flow(env, plan)
        prefix, _ = expected(flow, plan, parameters=case['state']['parameters'])
        robot = clone_robot(env.robot)
        check = robot_check(robot, env, prefix, item=case['item'])
        assert check['feasible']
        closed = sweep(env, case['item'], command=robot.get_joint())
        save(folder / 'closure.json', closed)
        if not closed['passed']:
            assert unchanged(before, fingerprint(env))['passed']
            return dict(status='rejected', stage='gripper_closure')
        context = SimpleNamespace(env=env, robot=env.robot, q0=flow.q0.copy(), q1=flow.q0.copy(), T_wo=flow.T_wo)
        commands = native_commands(context, case, plan=plan, folder=folder / 'native')
        save(folder / 'commands.json', commands)
        try:
            observe(env, case['config'], folder=folder / 'initial_observation')
        except ObservationRejected:
            return dict(status='rejected', stage='initial_observation')
        isolation = unchanged(before, fingerprint(env))
    save(folder / 'preflight.json', dict(passed=commands['passed'], closure_passed=True,
                                        initial_qualified=True, state_matches=True, isolation=isolation))
    return dict(status='ready', stage='complete_static_preflight')


def evaluate(action, *, history, geometry, folder):
    allowed = permitted(action, history)
    if allowed != 'proposal':
        return dict(status=allowed, stage=None)
    observation = read(PROJECT / f'qualified_intent_v1/run/{SEED}/observation.json')
    proposal = propose(observation['target_points'], observation['nominal'], action)
    save(folder / 'proposal.json', proposal)
    if proposal['status'] != 'proposal':
        return dict(status='rejected', stage='grasp_proposal')
    case = read(PROJECT / 'qualified_task_v1/run/manifest.json')['cases'][str(SEED)]
    result = inspect(case, proposal, geometry=geometry)
    save(folder / 'private_plan.json', result)
    public = outcome(result)
    if public['status'] != 'ready':
        return public
    return extra(case, result['plan'], folder)
