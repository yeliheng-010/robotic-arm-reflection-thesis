"""预先声明开发条件与运行顺序。"""
from pathlib import Path
import random

ROOT = Path('/home/yeliheng/grasp_server/refinement_v2')
CASES = (7, 11, 22, 23, 25, 30, 31, 32, 37, 42, 44, 47)
ARMS = ('rule_old', 'rule_new', 'flash_old', 'flash_new')
REPEATS = 3
ORDER_SEED = 20261024
PROBES = ((32, 1, 'direction'), (47, 1, 'duration'), (46, 1, 'candidate'),
          (42, 1, 'bounds'), (29, 2, 'repeat'), (22, 1, 'missing'))
COLLISION_HEIGHTS = (None, .06, .19, .25, .30, .35)
COLLISION_CASES = (0, 24)
SIM_PYTHON = '/home/yeliheng/grasp_server/env_sim/bin/python'
WORKER_TIMEOUT = 1800


def runs(mode):
    cases = (22, 32) if mode == 'smoke' else CASES
    rows = [dict(case=case, arm=arm, repeat=repeat)
            for case in cases for arm in ARMS
            for repeat in range(REPEATS if arm.startswith('flash') and mode != 'smoke' else 1)]
    random.Random(ORDER_SEED).shuffle(rows)
    return rows


def run_id(item):
    return f"{item['case']:02d}_{item['arm']}_{item['repeat']}"
