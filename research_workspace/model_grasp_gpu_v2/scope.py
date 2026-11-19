from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch
from model_grasp_gpu_v1 import common

ROOT = Path(__file__).resolve().parent
BUDGET = dict(decisions=3, planning=4, observations=0)


@contextmanager
def bind(*modules):
    with ExitStack() as stack:
        for module in (common,*modules):
            stack.enter_context(patch.object(module,'ROOT',ROOT))
            if hasattr(module,'BUDGET'):
                stack.enter_context(patch.object(module,'BUDGET',BUDGET))
        yield
