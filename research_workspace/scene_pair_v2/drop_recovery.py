"""已对准但抬升掉落时，第三次优先使用经过路径检查的竖直抓取。"""
from contextlib import contextmanager
import math
from unittest.mock import patch

CENTER_TOLERANCE_M = .002
RECOVERY_ATTEMPT = 3


def eligible(report):
    if not report or report.get('error_type') != 'object_dropped':
        return False
    evidence = report.get('evidence', {})
    if evidence.get('motion_context', {}).get('phase') != 'carry_lift':
        return False
    residual = evidence.get('grasp_residual_xy')
    if not isinstance(residual, (list, tuple)) or len(residual) != 2:
        return False
    if not all(type(v) in (int, float) and math.isfinite(v) for v in residual):
        return False
    return math.hypot(*residual) <= CENTER_TOLERANCE_M


def enabled(*, index, report):
    return index == RECOVERY_ATTEMPT and eligible(report)


def vertical_first(nominal):
    from cm_pose import poses
    rows = poses(nominal)
    return rows[1:] + rows[:1]


@contextmanager
def context(report, *, index):
    if not enabled(index=index, report=report):
        yield
        return
    import cm_runtime
    import cm_planning
    previous = cm_runtime.eligible
    with patch.object(cm_runtime, 'eligible', lambda value: previous(value) or eligible(value)), \
         patch.object(cm_planning, 'poses', vertical_first):
        yield


def attempt(item, state, *, directory, policy, feedback):
    from cm_runtime import attempt as original
    with context(feedback, index=RECOVERY_ATTEMPT):
        return original(item, state, directory=directory, policy=policy, feedback=feedback)
