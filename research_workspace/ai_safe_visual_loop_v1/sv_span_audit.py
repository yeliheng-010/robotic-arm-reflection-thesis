from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import sv_audit_attempt
from span_audit import context as span_context
from sv_common import read

original_route = sv_audit_attempt.route
original_inspect = sv_audit_attempt.inspect


def route(case, step, record):
    folder = Path(step['session_path'])
    calibration = read(folder/'observation_summary.json')['private'][0]
    with span_context(folder, calibration):
        return original_route(case, step, record)


def inspect(case, step):
    value = original_inspect(case, step)
    assert value['contact']['self_contact_samples'] == 0
    return value


@contextmanager
def context():
    import sv_audit_replay
    with patch.object(sv_audit_attempt, 'route', route), patch.object(sv_audit_replay, 'inspect', inspect):
        yield
