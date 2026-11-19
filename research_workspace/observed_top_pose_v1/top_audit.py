from pathlib import Path
from unittest.mock import patch
import numpy as np
import nc_audit_attempt
from rb_audit import route
from span_audit import context as span_context
from top_runtime import audit_context
from top_motion import motion
from f_common import read


def audit_attempt(case, step):
    folder = Path(step['session_path'])
    if step['strategy'] == 'original':
        record, recorder, groups = nc_audit_attempt.audit(case, step)
    else:
        assert step['strategy'] == 'observed_top'
        with patch.object(nc_audit_attempt, 'motion', motion):
            record, recorder, groups = nc_audit_attempt.audit(case, step)
        plan, bridge = read(folder/'route.json'), read(folder/'bridge.json')
        if bridge.get('grasp'):
            assert plan['selected'] is not None
            np.testing.assert_allclose(plan['selected']['pose'], bridge['observed_target']['commanded_pose'], rtol=0, atol=1e-12)
    calibration = read(folder/'observation_summary.json')['private'][0]
    context = audit_context if step['strategy'] == 'observed_top' else span_context
    with context(folder, calibration):
        geometry = route(case, step, record)
    return record, geometry
