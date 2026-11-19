"""固定相机坐标网格；完整保留原夹爪几何与检测判据。"""
import numpy as np
from grasp_process import ModelFreeCollisionDetector as OriginalDetector


def fixed_voxels(points, voxel_size):
    values = np.asarray(points, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 3 or not np.isfinite(values).all():
        raise ValueError('点云必须是有限N×3数组')
    if not np.isfinite(voxel_size) or voxel_size <= 0:
        raise ValueError('体素大小必须为正数')
    if len(values) == 0:
        return values.copy()
    keys = np.floor(values / voxel_size).astype(np.int64)
    _, inverse, counts = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
    sums = np.zeros((len(counts), 3), dtype=np.float64)
    np.add.at(sums, inverse, values)
    return sums / counts[:, None]


class StableDetector(OriginalDetector):
    def __init__(self, scene_points, voxel_size=.005):
        # 父类仍提供真实夹爪尺寸，避免复制检测实现；只替换下采样结果。
        super().__init__(scene_points, voxel_size=voxel_size)
        self.scene_points = fixed_voxels(scene_points, voxel_size)
