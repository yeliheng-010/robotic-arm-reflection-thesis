"""独立修订入口；旧冻结执行器、物理尝试和原保护均保留。"""
from contextlib import contextmanager
from unittest.mock import patch
import loopstudy.runtime as loop
import op_runtime
import op_runtime_v2
from oc_planning import factory, plans


@contextmanager
def wiring():
    with patch.object(loop, 'plans', plans), patch.object(op_runtime, 'factory', factory):
        yield


class Session(op_runtime_v2.Session):
    def _engine(self):
        with wiring():
            super()._engine()


class PreviewSession(op_runtime_v2.PreviewSession):
    def _engine(self):
        with wiring():
            super()._engine()
