"""由观测点云和标定生成世界竖直候选，不读取物体真值位置。"""
import numpy as np
from stability.proposals import generate as original
from grasp_process import GraspGroup

DOWN_FRAME = np.diag([1., -1., -1.])


def generate(points, camera):
    rotation = np.asarray(camera['rotation']) @ DOWN_FRAME
    position = np.asarray(camera['position'])
    world = np.asarray(points) @ rotation.T + position
    group = original(world @ DOWN_FRAME)
    rows = group.grasp_group_array.copy()
    rows[:, 13:16] = (rows[:, 13:16] @ DOWN_FRAME-position) @ rotation
    transforms = rows[:, 4:13].reshape(-1, 3, 3)
    rows[:, 4:13] = (rotation.T @ DOWN_FRAME @ transforms).reshape(-1, 9)
    return GraspGroup(rows)
