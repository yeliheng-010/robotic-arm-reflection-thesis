"""同一观测的不同候选阶段分别审计，不关闭原单阶段一致性断言。"""
from contextlib import contextmanager
from contextvars import ContextVar
from unittest.mock import patch
import top_runtime
from top_runtime import filter_context as original_filter

CURRENT = ContextVar('joint_policy_observation')


@contextmanager
def observation(points, trace):
    token = CURRENT.set((points,trace,[]))
    try:
        yield
    finally:
        CURRENT.reset(token)


def stage(generator, callback):
    points,trace,history = CURRENT.get()
    local = {}
    with patch.object(top_runtime,'candidates',generator),original_filter(points,local):
        result = callback()
    history.append(local)
    trace.update(local)
    trace['candidate_stages'] = list(history)
    return result
