"""直接MJB资源边界：禁止重建场景、渲染、规划和live再次forward。"""
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
from pathlib import Path
import mujoco
from qualified_closure_mjb_v1.protocol import PROJECT, proposal, require
from qualified_closure_mjb_v1.limits import StepGate


class Resources:
    def __init__(self):
        self.gate = StepGate(mujoco.mj_step)
        self.model, self.allow_load = None, False
        self.counts = dict(binary_load=0, data_construction=0, live_forward=0, copy_forward=0,
                           forbidden=0, reset=0, compile=0, rendering=0, planning=0, optimizer=0, close=0)
        self.original_load = mujoco.MjModel.from_binary_path
        self.original_data, self.original_forward = mujoco.MjData, mujoco.mj_forward

    def load(self, path):
        require(self.allow_load and self.counts['binary_load'] == 0, 'Unexpected model load')
        require(Path(path).resolve() == (PROJECT/proposal()['model']['path']).resolve(), 'Wrong MJB')
        self.counts['binary_load'] += 1
        self.model = self.original_load(path)
        return self.model

    def data(self, model):
        require(model is self.model and model is not None, 'Wrong data model')
        self.counts['data_construction'] += 1
        return self.original_data(model)

    def forward(self, model, data):
        require(model is self.model and model is not None, 'Wrong forward model')
        live = data is self.gate.data
        if live:
            require(self.gate.stage == 'blocked' and self.counts['live_forward'] == 0,
                    'Live forward forbidden after initial restore')
        self.counts['live_forward' if live else 'copy_forward'] += 1
        return self.original_forward(model, data)

    def blocked(self, label):
        def call(*args, **kwargs):
            self.counts[label] += 1
            raise RuntimeError('MJB diagnostic forbids '+label)
        return call

    def summary(self):
        return dict(self.counts, integration=self.gate.requests, native_returns=self.gate.returns,
                    setup_steps=0)


def block_runtime(stack, resources):
    import grasp_process
    from scipy import optimize
    from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
    targets = ((UR5GraspEnv, '__init__', 'reset'), (UR5GraspEnv, 'reset', 'reset'),
        (UR5GraspEnv, 'step', 'forbidden'), (mujoco.Renderer, '__init__', 'rendering'),
        (mujoco.Renderer, 'render', 'rendering'), (grasp_process.GraspFlow, 'close_gripper', 'close'),
        (grasp_process, 'close_gripper', 'close'), (grasp_process, '_run_planners', 'planning'),
        (optimize, 'minimize', 'optimizer'), (optimize, 'least_squares', 'optimizer'))
    for owner, name, label in targets:
        stack.enter_context(patch.object(owner, name, resources.blocked(label)))


@contextmanager
def guarded():
    resources = Resources()
    with ExitStack() as stack:
        for name in ('mj_step1', 'mj_step2'):
            stack.enter_context(patch.object(mujoco, name, resources.blocked('forbidden')))
        for name in ('from_xml_path', 'from_xml_string'):
            stack.enter_context(patch.object(mujoco.MjModel, name, resources.blocked('compile')))
        for name in ('from_file', 'from_string', 'compile', '__init__'):
            stack.enter_context(patch.object(mujoco.MjSpec, name, resources.blocked('compile')))
        for owner, name, call in ((mujoco, 'mj_step', resources.gate.call),
                                  (mujoco, 'MjData', resources.data),
                                  (mujoco, 'mj_forward', resources.forward),
                                  (mujoco.MjModel, 'from_binary_path', resources.load)):
            stack.enter_context(patch.object(owner, name, call))
        block_runtime(stack, resources)
        try:
            yield resources
        finally:
            resources.gate.stage = 'blocked'
            resources.gate.pending = False
