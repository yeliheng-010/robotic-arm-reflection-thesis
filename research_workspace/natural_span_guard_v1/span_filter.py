from contextlib import contextmanager
from unittest.mock import patch
import numpy as np
from cm_pose import poses as original
from geometry.candidates import MAX_WIDTH, WIDTH_MARGIN
from span import span


def measured(nominal, points):
    rows = []
    for pose in original(nominal):
        width = span(points, pose['pose'].R[:,1])
        rows.append(dict(id=pose['id'], pose=pose['pose'], observed_span_m=width,
            required_width_m=width+WIDTH_MARGIN, passed=width+WIDTH_MARGIN <= MAX_WIDTH))
    return rows


def filtered(points, trace):
    def generate(nominal):
        rows = measured(nominal, points)
        public = [{k:v for k,v in r.items() if k != 'pose'} for r in rows]
        if 'poses' in trace:
            assert trace['poses'] == public
        trace['poses'] = public
        return [dict(id=r['id'], pose=r['pose']) for r in rows if r['passed']]
    return generate


@contextmanager
def context(points, trace):
    import rv_runtime
    with patch.object(rv_runtime, 'poses', filtered(points, trace)):
        yield
