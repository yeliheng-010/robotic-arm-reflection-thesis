"""以原完整保护器校验每条搜索边；不改变真实仿真状态。"""
import math
import numpy as np
from rh_planner import evaluate, planners
from routecheck.clone import clone_robot
from routecheck.static import state, unchanged

SPEED_LIMIT = 1.
ACCELERATION_LIMIT = 2.
QUINTIC_SPEED = 1.875
QUINTIC_ACCELERATION = 10/math.sqrt(3)


def duration(start, goal, minimum):
    delta = max(abs(a-b) for a,b in zip(start,goal))
    return max(minimum, QUINTIC_SPEED*delta/SPEED_LIMIT,
               math.sqrt(QUINTIC_ACCELERATION*delta/ACCELERATION_LIMIT))


def option(path, minimum):
    return dict(id='rrt_connect',waypoints=path,
                durations=[duration(a,b,minimum) for a,b in zip(path,path[1:])])


class EdgeChecker:
    def __init__(self, flow, case):
        self.flow, self.case, self.last = flow, case, None
        self.minimum = case['state']['parameters']['time_scale']

    def __call__(self, start, goal):
        before = state(self.flow.robot,self.flow.env)
        robot = clone_robot(self.flow.robot)
        robot.set_joint(np.array(start))
        self.last = evaluate(option([start,goal],self.minimum),robot,
                             self.flow.env,item=self.case['item'])
        unchanged(before,state(self.flow.robot,self.flow.env))
        return bool(self.last['feasible'])


def segments(path, minimum):
    selected = option(path,minimum)
    return [('pregrasp',p,t) for p,t in zip(planners(selected),selected['durations'])]
