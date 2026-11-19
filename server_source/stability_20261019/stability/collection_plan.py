"""先冻结任务组，再采集；整组来源-目标组合只属于一个split。"""
from stability.experiment import SOURCES

FAULTS = ('calibration', 'collision', 'placement')
DESTINATIONS = ('BlueBin', 'RedBin', 'SortingTray')
HELDOUT = {('RedBlock', 'SortingTray'): 'validation', ('GreenCylinder', 'RedBin'): 'validation',
           ('PurpleCapsule', 'SortingTray'): 'test', ('OrangeSphere', 'RedBin'): 'test'}
LIMITS = {'train': 1000, 'validation': 100, 'test': 100}
MIN_PER_FAULT = 100


def task_plan(stage):
    if stage == 'pilot':
        return [dict(source=s, destination='BlueBin', fault=f, seed=6000, split='train')
                for s in SOURCES for f in FAULTS]
    tasks = []
    for offset in range(200):
        for source in SOURCES:
            for destination in DESTINATIONS:
                split = HELDOUT.get((source, destination), 'train')
                if split != 'train' and offset >= 75:
                    continue
                seed = {'train': 10000, 'validation': 20000, 'test': 30000}[split]+offset
                tasks.extend(dict(source=source, destination=destination, fault=f,
                                  seed=seed, split=split) for f in FAULTS)
    return tasks

