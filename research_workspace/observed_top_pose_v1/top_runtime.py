from contextlib import contextmanager
from unittest.mock import patch
import numpy as np
import spatialmath as sm
import span_filter
import span_runtime
import span_audit
from top_fit import estimate

MAX_TRANSLATION_M = .050


def candidates(nominal, fitted):
    if not fitted['available']:
        return []
    center, axis = np.array(fitted['center']), np.array(fitted['closing_axis'])
    if np.linalg.norm(center-nominal.t) > MAX_TRANSLATION_M:
        return []
    return [dict(id=f'observed_top_{degree}', pose=sm.SE3.Rt(sm.SO3.TwoVectors(x=[0.,0.,-1.],y=sign*axis), center))
        for degree,sign in ((0,1), (180,-1))]


@contextmanager
def filter_context(points, trace):
    fitted = estimate(points)
    trace['observed_top_estimate'] = fitted
    def poses(nominal):
        return candidates(nominal, fitted)
    with patch.object(span_filter, 'original', poses), span_filter.context(points, trace):
        yield


class TopSession(span_runtime.SpanSession):
    def _engine(self):
        assert self.state['parameters']['grasp_offset'] == [0.,0.,0.]
        with patch.object(span_runtime, 'filter_context', filter_context):
            super()._engine()


@contextmanager
def audit_context(folder, calibration):
    with patch.object(span_audit, 'filter_context', filter_context):
        with span_audit.context(folder, calibration) as trace:
            yield trace
        recorded = span_audit.read(folder/'span_guard.json')
        if recorded['active']:
            assert trace['observed_top_estimate'] == recorded['observed_top_estimate']
