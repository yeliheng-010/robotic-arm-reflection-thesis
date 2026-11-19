from contextlib import contextmanager
from unittest.mock import patch
import guard_runtime
from contact_policy import forbidden


@contextmanager
def context(item, trace, *, contacts=True):
    with patch.object(guard_runtime, 'forbidden', forbidden), guard_runtime.context(item, trace, contacts=contacts):
        yield
