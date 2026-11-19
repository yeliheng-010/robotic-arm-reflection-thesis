"""只在隔离实验内兼容旧的相机检查记录。"""
from copy import deepcopy


def normalized(record):
    current = deepcopy(record)
    current.setdefault('calibration', None)
    current['accepted'] = False
    return current
