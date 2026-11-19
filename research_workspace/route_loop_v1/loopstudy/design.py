"""开发锚点与两个额外种子在运行前共同冻结。"""
from pathlib import Path
from recovery.references import scene_items,scene_build

ROOT = Path('/home/yeliheng/grasp_server/route_loop_v1')
ARMS = ('retry','old_rule','new_rule','hybrid')
MAX_ATTEMPTS = 3
ANCHOR_SEED = 905001
SEEDS = (ANCHOR_SEED,905002,905003)


def items():
    scenes = [r for r in scene_items() if r['source']=='PurpleCapsule' and r['seed'] in SEEDS]
    return [dict(s,id=s['id']+'_'+arm,scene_id=s['id'],arm=arm) for s in scenes for arm in ARMS]


def configuration(item):
    return scene_build(item['seed'],item['factor'])
