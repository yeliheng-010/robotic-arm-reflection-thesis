"""先冻结布局及按种子分组的数据用途，再观察任何恢复结果。"""
from pathlib import Path
import numpy as np
from controlled.config import scenario
from diversity.config import layout
from noisyloop.feedback import projection
from stability.collection_plan import HELDOUT

ROOT=Path('/home/yeliheng/grasp_server/scene_expansion_v1')
SEEDS=tuple(range(910001,910011))
RESERVED_TEST_SEEDS=tuple(range(910101,910111))
PAIRS=(('RedBlock','BlueBin'),('PurpleCapsule','RedBin'))
FACTORS={'position_1cm':(.01,0.,0.),'position_3cm':(.03,0.,0.),
         'yaw_30deg':(0.,30.,0.),'combined':(.02,20.,0.),'container_1cm':(0.,0.,.01)}
ARMS=('new_rule','hybrid')
MAX_ATTEMPTS=3
TRAIN_SEED_COUNT=8
SMOKE_FACTORS=tuple(FACTORS)[:3]


def scenes():
    rows=[]
    for pair_index,(source,destination) in enumerate(PAIRS):
        assert HELDOUT.get((source,destination))!='test'
        for factor_index,factor in enumerate(FACTORS):
            for seed_index,seed in enumerate(SEEDS):
                noise_index=(pair_index*len(FACTORS)+factor_index+seed_index)%len(projection.profiles())
                key=f'E{pair_index}_{seed}_{factor}'
                rows.append(dict(id=key,scene_id=key,pair_id=key,source=source,destination=destination,
                    seed=seed,factor=factor,factor_index=factor_index,noise_index=noise_index,
                    noise_profile=projection.profiles()[noise_index],noise_repeat=0,
                    split='train_candidate' if seed_index<TRAIN_SEED_COUNT else 'development_validation'))
    return rows


def items():
    return [dict(s,id=s['id']+'_'+arm,arm=arm) for s in scenes() for arm in ARMS]


def configuration(item):
    xy,yaw,container=FACTORS[item['factor']]
    result=scenario(item['seed'],'clean')
    result.update(version='scene-expansion-v1',level=item['factor'])
    result['profile'].update(xy_m=xy,yaw_degrees=yaw,container_xy_m=container)
    positions,rejected=layout(np.random.default_rng(np.random.SeedSequence([item['seed'],921])),result['profile'])
    yaw_rng=np.random.default_rng(np.random.SeedSequence([item['seed'],922]))
    for body,position in zip(result['bodies'].values(),positions):
        body.update(xy=position,yaw_delta=float(np.radians(yaw_rng.uniform(-yaw,yaw))))
    rng=np.random.default_rng(np.random.SeedSequence([item['seed'],923]))
    result['containers']={name:rng.uniform(-container,container,2).tolist() for name in result['containers']}
    result['layout_rejections']=rejected
    return result


def is_smoke(item):
    return item['seed']==SEEDS[0] and item['factor'] in SMOKE_FACTORS
