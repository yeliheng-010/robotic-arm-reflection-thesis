"""独立进程内的场景与挡板绑定，控制组不启用任何干预。"""
from contextlib import contextmanager,ExitStack
from unittest.mock import patch
from loopstudy import episode,audit
from recovery.references import collision_context,scene_protocol
from hardstudy.design import configuration


@contextmanager
def bound(item,*,enabled=True):
    def context(current,trace):
        active=enabled and item['injection']['collision']
        return collision_context(dict(current,enabled=active),trace)
    with ExitStack() as stack:
        stack.enter_context(patch.object(episode,'configuration',configuration))
        stack.enter_context(patch.object(audit,'configuration',configuration))
        stack.enter_context(patch.object(episode,'collision_context',context))
        yield


def geometry(item):
    reference=scene_protocol.reference
    with patch.object(reference,'scenario',lambda seed,group:configuration(item)):
        return reference.geometry_check(dict(item,enabled=True))
