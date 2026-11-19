"""先冻结诊断槽位与预算，全部依据观测几何，不读取真值。"""
from itertools import combinations
from visibility_calibration_v1.policy import angle

SEEDS = tuple(range(978101, 978113))
CAMERA_BUDGET = 256
REPEATS = 3
MAX_PAIRS = 3
NOISE_PREFIX = 978501
OFFSETS = ((0., 0.), (-20., 0.), (20., 0.), (0., -12.), (0., 12.))


def pairs(rows):
    valid = [row for row in rows if row['calibration_passed'] is True]
    eligible = [(a['index'], b['index']) for a, b in combinations(valid, 2)
                if angle(a['camera'], b['camera']) >= 10.]
    return eligible[:MAX_PAIRS]
