"""用原路径保护检查候选；规划只读当前物理状态。"""
import numpy as np
import grasp_process as grasp
from routecheck.clone import clone_robot
from route_geometry import inspect
from rh_policy import candidates, first_approved


def planners(option):
    rows = []
    for start, end, duration in zip(option['waypoints'], option['waypoints'][1:], option['durations']):
        parameter = grasp.JointParameter(np.asarray(start), np.asarray(end))
        velocity = grasp.QuinticVelocityParameter(duration)
        rows.append(grasp.TrajectoryPlanner(grasp.TrajectoryParameter(parameter, velocity)))
    return rows


def evaluate(option, robot, env, *, item):
    segments = [('back_to_zero_'+str(i), p, t)
                for i, (p, t) in enumerate(zip(planners(option), option['durations']))]
    return inspect(clone_robot(robot), env, segments, item=item)


def select(robot, env, goal, *, duration, item):
    start = robot.get_joint().copy()
    qpos = env.mj_data.qpos.copy()
    selected, attempts = first_approved(candidates(start.tolist(), list(goal), duration=duration),
        lambda option: evaluate(option, robot, env, item=item))
    np.testing.assert_array_equal(qpos, env.mj_data.qpos)
    np.testing.assert_array_equal(start, robot.get_joint())
    return dict(selected=selected, attempts=attempts, unchanged_qpos=True,
                unchanged_robot_q=True, duration_limit=2*duration)
