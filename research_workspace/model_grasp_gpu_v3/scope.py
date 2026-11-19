from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from model_grasp_gpu_v2 import scope as original

ROOT = Path(__file__).resolve().parent
BUDGET = dict(decisions=2, planning=4, observations=0)


@contextmanager
def bind(*modules):
    with patch.object(original,'ROOT',ROOT),patch.object(original,'BUDGET',BUDGET):
        with original.bind(*modules):
            yield
