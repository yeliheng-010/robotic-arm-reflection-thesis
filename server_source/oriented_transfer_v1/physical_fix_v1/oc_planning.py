"""计划收集只构建命令；实时持物保护和排他记录仅在执行入口运行。"""
from contextvars import ContextVar
from inspect import signature
import numpy as np
import grasp_process as grasp
from routecheck.adapter import plans as original_plans
from commands import build
from op_carry import factory as execution_factory

COLLECTING = ContextVar('oriented_transfer_collecting', default=False)


def plans(original, context, values):
    token = COLLECTING.set(True)
    try:
        return original_plans(original, context, values)
    finally:
        COLLECTING.reset(token)


def factory(original, trace, *, session):
    execute = execution_factory(original, trace, session=session)

    def move(*args, **kwargs):
        if not COLLECTING.get():
            return execute(*args, **kwargs)
        bound = signature(original).bind(*args, **kwargs)
        bound.apply_defaults()
        values = bound.arguments
        selected = trace['selected']['held_selection']
        np.testing.assert_allclose(selected['prefix']['pose'], values['T_start'].A,
            atol=1e-6, rtol=0)
        paths, times, poses = build(selected, values['time4'])
        action = grasp._run_planners(values['robot'], values['env'], paths,
            [0., *times], values['action'], values['dt'])
        return action, poses

    return move
