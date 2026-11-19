"""一次permit仅能对绑定live状态推进一次；请求与返回独立计数。"""
from qualified_closure_mjb_v1.protocol import BUDGET, require


class StepGate:
    def __init__(self, original):
        self.original = original
        self.stage, self.pending = 'blocked', False
        self.requests = self.returns = 0
        self.model = self.data = None

    def bind(self, model, data):
        require(self.model is None and self.data is None, 'Cannot rebind live state')
        self.model, self.data = model, data

    def arm(self, model, data):
        require(self.stage == 'task' and not self.pending, 'Step permit forbidden')
        require(model is self.model and data is self.data, 'Wrong permit target')
        require(self.requests < BUDGET['task_steps'], 'Step budget exhausted')
        self.pending = True

    def call(self, model, data, *, nstep=1):
        require(self.stage == 'task' and self.pending, 'Unscheduled native step')
        require(model is self.model and data is self.data, 'Wrong live model/data')
        require(type(nstep) is int and nstep == 1, 'Frame skip forbidden')
        require(self.requests < BUDGET['task_steps'], 'Step budget exhausted')
        self.pending = False
        self.requests += 1
        result = self.original(model, data)
        self.returns += 1
        return result


def forbid(*args, **kwargs):
    raise RuntimeError('Split step, nested closure or environment construction forbidden')
