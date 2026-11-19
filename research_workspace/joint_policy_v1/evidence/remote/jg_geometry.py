"""由当前关节与真实限位选择安全表示，不读取条件编号。"""
import numpy as np
from bounded_ik import limits
from jr_angles import candidates
from js_geometry import option as timed_option
from rh_planner import evaluate
from routecheck.clone import clone_robot
from routecheck.static import state, unchanged
from jg_policy import Budget,select

MAX_CHECKS = 256


class Advisor:
    def __init__(self, flow, *, item, parameters, record):
        self.flow,self.item,self.record = flow,item,record
        self.minimum = parameters['time_scale']
        self.bounds = limits(flow.env.mj_model).tolist()
        self.budget,self.last = Budget(MAX_CHECKS),None

    def alternatives(self, start, goal):
        for value in candidates(start,goal,bounds=self.bounds):
            if np.array_equal(value,goal):
                continue
            np.testing.assert_allclose(self.flow.robot.fkine(np.array(value)).A,
                self.flow.robot.fkine(np.array(goal)).A,atol=1e-8,rtol=0)
            yield dict(timed_option([start,value],self.minimum),id='equivalent_joint_angles')

    def check(self, option):
        before = state(self.flow.robot,self.flow.env)
        robot = clone_robot(self.flow.robot)
        robot.set_joint(np.array(option['waypoints'][0]))
        self.last = evaluate(option,robot,self.flow.env,item=self.item)
        unchanged(before,state(self.flow.robot,self.flow.env))
        return bool(self.last['feasible'])

    def choose(self, row):
        start,goal = self.flow.q0.tolist(),row['q1']
        original = dict(id='original',waypoints=[start,goal],durations=[self.minimum])
        def record(event):
            self.record(dict(event,check=self.last))
        selected = select(original,self.alternatives(start,goal),check=self.check,
                          budget=self.budget,record=record)
        if selected is None:
            return None
        if selected is original:
            return row
        return dict(row,q1=selected['waypoints'][-1],joint_option=selected)
