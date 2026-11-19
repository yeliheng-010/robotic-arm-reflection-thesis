"""采集协议专用命名，避免与历史恢复器 rc_common 模块冲突。"""
import os
from pathlib import Path
from f_common import read, save, sha

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
BATCH = int(os.environ.get('RECOVERY_BATCH', '0'))
BATCH_SIZE = 32
TRAIN_PER_BATCH = 24
START_SEED = 964001
MAX_BATCHES = 32
BRANCHES = ('top_then_slow', 'lower_then_slow', 'slow_then_top')
BASE = ROOT/'batches'/f'{BATCH:03d}'
QUAL = BASE/'qualification'
PHYSICS = BASE/'physics'


def seeds(batch):
    assert type(batch) is int and 0 <= batch < MAX_BATCHES
    start = START_SEED+batch*BATCH_SIZE
    return tuple(range(start, start+BATCH_SIZE))


def split(seed):
    assert START_SEED <= seed < START_SEED+MAX_BATCHES*BATCH_SIZE
    return 'train' if (seed-START_SEED) % BATCH_SIZE < TRAIN_PER_BATCH else 'dev'


def verify(path):
    value = read(path)
    assert all(sha(p) == h for p,h in value['identities'].items())
    return value


def action(branch, index):
    top = dict(id='SET_GRASP_STRATEGY', args=dict(value='observed_top'))
    slow = dict(id='SET_TIME_SCALE', args=dict(value=3.))
    lower = dict(id='SET_GRASP_OFFSET', args=dict(delta_m=[0.,0.,-.03]))
    actions = dict(top_then_slow=(top,slow), lower_then_slow=(lower,slow), slow_then_top=(slow,top))
    assert index in (0,1)
    return actions[branch][index]
