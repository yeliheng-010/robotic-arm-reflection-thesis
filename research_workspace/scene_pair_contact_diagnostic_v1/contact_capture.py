"""动作外包只读采样，异常不吞掉，所有patch限定在本次诊断。"""
import json
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
import grasp_process as grasp
from reflection.monitors import ExecutionMonitor
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from reflection.sim_sensing import pad_contacts
from contact_data import sample

STRIDE = 10
ACTIONS = ('move_to_grasp_pose', 'close_gripper', 'move_to_point', 'open_gripper', 'back_to_zero')


class Recorder:
    def __init__(self, stream, item):
        self.stream, self.item = stream, item
        self.action, self.count, self.previous = 'idle', 0, None

    def write(self, env, *, event):
        row = sample(env, self.item)
        row.update(action=self.action, event=event, step=self.count)
        self.stream.write(json.dumps(row, ensure_ascii=False)+'\n')

    def step(self, original):
        def observed(env, action=None):
            try:
                return original(env, action)
            finally:
                if self.action != 'idle':
                    self.capture_step(env)
        return observed

    def capture_step(self, env):
        self.count += 1
        touched = pad_contacts(env.mj_model, env.mj_data)
        signature = tuple(tuple(sorted(touched[k])) for k in ('left', 'right'))
        if signature != self.previous or self.count % STRIDE == 0:
            self.write(env, event='contact_change' if signature != self.previous else 'sample')
        self.previous = signature

    def method(self, original, name):
        def observed(flow, *args, **kwargs):
            self.action = name
            self.write(flow.env, event='begin')
            try:
                return original(flow, *args, **kwargs)
            finally:
                self.write(flow.env, event='end_or_abort')
        return observed

    def check(self, original):
        def observed(monitor, residual):
            self.write(monitor.env, event='check_grasp')
            return original(monitor, residual)
        return observed


@contextmanager
def capture(path, item):
    with path.open('x', encoding='utf-8') as stream, ExitStack() as stack:
        recorder = Recorder(stream, item)
        stack.enter_context(patch.object(UR5GraspEnv, 'step', recorder.step(UR5GraspEnv.step)))
        stack.enter_context(patch.object(ExecutionMonitor, 'check_grasp', recorder.check(ExecutionMonitor.check_grasp)))
        for name in ACTIONS:
            stack.enter_context(patch.object(grasp.GraspFlow, name, recorder.method(getattr(grasp.GraspFlow, name), name)))
        yield
