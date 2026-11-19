"""稳定实例身份与场景显示颜色分离。"""
import numpy as np

CONTAINERS = ('BlueBin', 'RedBin', 'SortingTray')
PALETTE = {'红色': (.85, .10, .10), '蓝色': (.10, .25, .85),
           '绿色': (.12, .70, .18), '黄色': (.90, .78, .08),
           '橙色': (.95, .40, .08), '紫色': (.60, .15, .80)}
SOURCE_LABELS = {'RedBlock': '红色方块', 'GreenCylinder': '绿色圆柱',
                 'PurpleCapsule': '紫色胶囊', 'OrangeSphere': '橙色小球'}


def sample(seed):
    rng = np.random.default_rng(np.random.SeedSequence([seed, 960202]))
    names = rng.choice(list(PALETTE), len(CONTAINERS), replace=False)
    result = {}
    for body, name in zip(CONTAINERS, names):
        rgb = np.clip(np.array(PALETTE[name])*rng.uniform(.85, 1.15), 0, 1)
        result[body] = dict(color=str(name), rgba=[*rgb.tolist(), 1.])
    return result


def labels(colors):
    result = dict(SOURCE_LABELS)
    result.update({name: value['color']+('托盘' if name=='SortingTray' else '箱子')
                   for name, value in colors.items()})
    return result
