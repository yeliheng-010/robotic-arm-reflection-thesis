"""先登记种子和条件，因素随机流互不干扰。"""
from pathlib import Path
from sd_appearance import sample as colors
from sd_camera import sample as camera

ROOT = Path('/home/yeliheng/grasp_server/scene_diversity_v2')
SEEDS = tuple(range(960101, 960113))
GROUPS = ('baseline', 'layout', 'appearance', 'camera', 'layout_camera', 'combined')
PAIRS = (('RedBlock', 'BlueBin'), ('PurpleCapsule', 'RedBin'))
SOURCES = ('RedBlock', 'GreenCylinder', 'PurpleCapsule', 'OrangeSphere')
CONTAINERS = ('BlueBin', 'RedBin', 'SortingTray')
MOVING = CONTAINERS + SOURCES
LAYOUT_GROUPS = ('layout', 'layout_camera', 'combined')
CAMERA_GROUPS = ('camera', 'layout_camera', 'combined')


def factors(seed, group):
    if type(seed) is not int or seed < 0 or group not in GROUPS:
        raise ValueError('Invalid seed or group')
    return dict(seed=seed, group=group, layout_enabled=group in LAYOUT_GROUPS,
                appearance=colors(seed) if group in ('appearance', 'combined') else {},
                camera=camera(seed) if group in CAMERA_GROUPS else None)


def items():
    return [dict(id=f'D{pair}_{seed}_{group}', seed=seed, group=group,
                 source=source, destination=destination, fault='none',
                 split='development_qualification')
            for seed in SEEDS for group in GROUPS
            for pair, (source, destination) in enumerate(PAIRS)]
