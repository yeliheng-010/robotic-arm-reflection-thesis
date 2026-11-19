"""6物理条件、6噪声配置、2实现、2方法，全部预登记。"""
from pathlib import Path
from loopstudy.design import items as previous_items,configuration,MAX_ATTEMPTS
from noisyloop.feedback import projection

ROOT=Path('/home/yeliheng/grasp_server/noisy_loop_v1')
ARMS=('new_rule','hybrid')
REPEATS=2


def items():
    scenes=[r for r in previous_items() if r['arm']=='new_rule']
    rows=[]
    for scene in scenes:
        for profile_index,profile in enumerate(projection.profiles()):
            for repeat in range(REPEATS):
                pair=f"{scene['scene_id']}_n{profile_index}_r{repeat}"
                rows.extend(dict(scene,id=pair+'_'+arm,pair_id=pair,arm=arm,
                    noise_index=profile_index,noise_profile=profile,noise_repeat=repeat) for arm in ARMS)
    return rows


def is_smoke(item):
    return item['seed']==905001 and item['factor']=='position_only' and item['noise_repeat']==0
