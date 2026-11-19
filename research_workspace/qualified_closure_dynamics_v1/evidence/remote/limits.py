"""原生步进的硬计数；审计、恢复和退出阶段均禁止积分。"""
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
from qualified_closure_dynamics_v1.protocol import BUDGET, require


class StepGate:
    def __init__(self, original):
        self.original = original
        self.stage = 'blocked'
        self.setup_steps = self.task_steps = 0
        self.pending = False
        self.model = self.data = None

    def call(self, model, data, *, nstep=1):
        require(nstep == 1, 'Frame skip forbidden')
        if self.stage == 'setup':
            require(self.setup_steps < BUDGET['setup_steps'], 'Setup budget exceeded')
            self.setup_steps += 1
        elif self.stage == 'task':
            require(self.pending, 'Unscheduled task step')
            require(model is self.model and data is self.data, 'Wrong live model/data')
            require(self.task_steps < BUDGET['task_steps'], 'Task budget exceeded')
            self.pending = False
            self.task_steps += 1
        else:
            raise RuntimeError('Integration forbidden in ' + self.stage)
        return self.original(model, data)

    def arm(self, model, data):
        require(self.stage == 'task' and not self.pending, 'Invalid step permit')
        self.model, self.data, self.pending = model, data, True


def forbid(*args, **kwargs):
    raise RuntimeError('Split integration or nested closure forbidden')


@contextmanager
def guarded(mujoco):
    gate = StepGate(mujoco.mj_step)
    with ExitStack() as stack:
        stack.enter_context(patch.object(mujoco, 'mj_step', gate.call))
        for name in ('mj_step1', 'mj_step2'):
            stack.enter_context(patch.object(mujoco, name, forbid))
        yield gate
