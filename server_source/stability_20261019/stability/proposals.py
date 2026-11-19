"""过滤前生成小范围合法位置候选；不读取任务标签。"""
from unittest.mock import patch
import numpy as np
import geometry.candidates as previous
from grasp_process import GraspGroup

ANGLES = tuple(range(10, 180, 10))
OFFSET = .008
SHIFTS = ((0, 0), (OFFSET, 0), (-OFFSET, 0), (0, OFFSET), (0, -OFFSET))
SHIFT_SCORE = .48
NMS_TRANSLATION = .004


def generate(points):
    with patch.object(previous, 'ANGLES_DEG', ANGLES):
        original = previous.generate(points)
    groups = [original.grasp_group_array.copy()]
    for dx, dy in SHIFTS[1:]:
        rows = original.grasp_group_array.copy()
        rows[:, 0] = SHIFT_SCORE
        rows[:, 13:15] += [dx, dy]
        groups.append(rows)
    return GraspGroup(np.concatenate(groups))


def filter_then_nms(group, detector):
    collision, empty = detector.detect(group, approach_dist=.06, collision_thresh=.01,
                                      return_empty_grasp=True, empty_thresh=.003)
    safe = group[~(collision | empty)]
    if len(safe) == 0:
        raise RuntimeError('所有候选均发生碰撞或夹爪内部为空')
    safe = safe.nms(translation_thresh=NMS_TRANSLATION)
    safe.sort_by_score()
    return safe

