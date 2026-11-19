"""只在独立worker进程内临时绑定新场景，退出时恢复。"""
from contextlib import contextmanager,ExitStack
from unittest.mock import patch
from loopstudy import episode,audit
from recovery.references import collision_context,scene_protocol
from expand.design import configuration


@contextmanager
def bound(item,*,enabled=True):
    def context(current,trace):
        return collision_context(dict(current,enabled=enabled),trace)
    with ExitStack() as stack:
        stack.enter_context(patch.object(episode,'configuration',configuration))
        stack.enter_context(patch.object(audit,'configuration',configuration))
        stack.enter_context(patch.object(episode,'collision_context',context))
        yield


def geometry(item):
    reference=scene_protocol.reference
    with patch.object(reference,'scenario',lambda seed,group:configuration(item)):
        return reference.geometry_check(dict(item,enabled=True))
