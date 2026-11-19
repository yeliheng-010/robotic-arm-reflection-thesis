"""第三次分支内临时排序；路径检查与动态监控保持原样。"""
from contextlib import contextmanager
from unittest.mock import patch
from collision_policy import eligible, ordered


@contextmanager
def context(feedback):
    if not eligible(feedback):
        yield
        return
    import cm_planning
    original = cm_planning.poses
    with patch.object(cm_planning, 'poses', lambda pose: ordered(original(pose))):
        yield
