"""加载真实运行模块前阻断模型/数据构造和全部积分入口。"""
import importlib
from contextlib import contextmanager, ExitStack
from unittest.mock import patch

RUNTIME_MODULES = (
    'grasp_process', 'qualified_execution_v1.environment',
    'qualified_closure_dynamics_v1.initial', 'qualified_closure_dynamics_v1.capture',
    'qualified_closure_dynamics_v1.backend', 'qualified_closure_dynamics_v1.worker',
    'qualified_closure_dynamics_v1.limits', 'qualified_closure_dynamics_v3.entry',
    'qualified_closure_dynamics_v3.preflight', 'qualified_closure_dynamics_v3.audit_imports')


def blocker(counts, label):
    def blocked(*args, **kwargs):
        counts[label] += 1
        raise RuntimeError('Zero-motion import check forbids ' + label)
    return blocked


@contextmanager
def zero_motion(mujoco=None):
    if mujoco is None:
        mujoco = importlib.import_module('mujoco')
    counts = dict(integration=0, model_construction=0, data_construction=0, spec_construction=0)
    with ExitStack() as stack:
        for name in ('mj_step', 'mj_step1', 'mj_step2'):
            stack.enter_context(patch.object(mujoco, name, blocker(counts, 'integration')))
        stack.enter_context(patch.object(mujoco, 'MjData', blocker(counts, 'data_construction')))
        for name in ('from_xml_path', 'from_xml_string', 'from_binary_path'):
            stack.enter_context(patch.object(mujoco.MjModel, name, blocker(counts, 'model_construction')))
        for name in ('from_file', 'from_string', 'compile'):
            stack.enter_context(patch.object(mujoco.MjSpec, name, blocker(counts, 'spec_construction')))
        yield counts


def load_runtime():
    from reflection.__main__ import bootstrap
    bootstrap()
    for name in RUNTIME_MODULES:
        importlib.import_module(name)
