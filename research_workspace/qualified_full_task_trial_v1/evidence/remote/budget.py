"""只限制本次运行的积分次数；不发起额外验证作业。"""
import time
from contextlib import contextmanager
from unittest.mock import patch
import mujoco

SETUP_LIMIT = 500
TASK_LIMIT = 20000
WALL_SECONDS = 600


class Budget:
    def __init__(self):
        self.phase = 'setup'
        self.target = None
        self.started = time.monotonic()
        self.counts = {p: dict(requests=0, returns=0) for p in ('setup', 'task')}
        self.native = mujoco.mj_step

    def step(self, model, data, nstep=1):
        if self.phase not in self.counts or nstep != 1:
            raise RuntimeError('Unauthorized integration phase or frame skip')
        row = self.counts[self.phase]
        limit = SETUP_LIMIT if self.phase == 'setup' else TASK_LIMIT
        if row['requests'] >= limit or time.monotonic() - self.started > WALL_SECONDS:
            raise RuntimeError('Single-attempt integration budget exhausted')
        if self.target is not None and not (model is self.target[0] and data is self.target[1]):
            raise RuntimeError('Integration model/data changed')
        row['requests'] += 1
        result = self.native(model, data)
        row['returns'] += 1
        return result

    def begin_task(self, env):
        self.target = (env.mj_model, env.mj_data)
        self.phase = 'task'


def forbidden(*args, **kwargs):
    raise RuntimeError('Split integration is not authorized')


@contextmanager
def limited():
    budget = Budget()
    with patch.object(mujoco, 'mj_step', budget.step), \
         patch.object(mujoco, 'mj_step1', forbidden), \
         patch.object(mujoco, 'mj_step2', forbidden):
        try:
            yield budget
        finally:
            budget.phase = 'blocked'
