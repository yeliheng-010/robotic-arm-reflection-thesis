"""五机制共享随机干预，固定400条目及按种子划分。"""
from pathlib import Path
import numpy as np
from controlled.config import scenario
from diversity.config import layout
from noisyloop.feedback import projection
from stability.collection_plan import HELDOUT

ROOT=Path('/home/yeliheng/grasp_server/hard_cases_v1')
SEEDS=tuple(range(920001,920021))
RESERVED_TEST_SEEDS=tuple(range(920101,920121))
PAIRS=(('RedBlock','BlueBin'),('PurpleCapsule','RedBin'))
FAMILIES=('grasp_bias','place_bias','collision','grasp_collision','grasp_place')
ARMS=('new_rule','hybrid')
MAX_ATTEMPTS=3
TRAIN_SEED_COUNT=16
LAYOUT_XY=.01
LAYOUT_YAW=12.
GRASP_RANGE=(.025,.065)
PLACE_RANGE=(.10,.18)


def biases(seed):
    rng=np.random.default_rng(np.random.SeedSequence([seed,930]))
    vectors=[]
    for low,high in (GRASP_RANGE,PLACE_RANGE):
        angle=rng.uniform(-np.pi,np.pi)
        radius=rng.uniform(low,high)
        vectors.append([float(radius*np.cos(angle)),float(radius*np.sin(angle)),0.])
    return vectors


def scenes():
    rows=[]
    for pair_index,(source,destination) in enumerate(PAIRS):
        assert HELDOUT.get((source,destination))!='test'
        for factor_index,factor in enumerate(FAMILIES):
            for seed_index,seed in enumerate(SEEDS):
                grasp,place=biases(seed)
                key=f'H{pair_index}_{seed}_{factor}'
                noise_index=(pair_index+factor_index+seed_index)%len(projection.profiles())
                rows.append(dict(id=key,scene_id=key,pair_id=key,source=source,destination=destination,
                    seed=seed,factor=factor,factor_index=factor_index,noise_index=noise_index,
                    noise_profile=projection.profiles()[noise_index],noise_repeat=0,
                    injection=dict(grasp=grasp if factor in ('grasp_bias','grasp_collision','grasp_place') else [0.,0.,0.],
                        place=place if factor in ('place_bias','grasp_place') else [0.,0.,0.],
                        collision=factor in ('collision','grasp_collision')),
                    split='train_candidate' if seed_index<TRAIN_SEED_COUNT else 'development_validation'))
    return rows


def items():
    return [dict(s,id=s['id']+'_'+arm,arm=arm) for s in scenes() for arm in ARMS]


def configuration(item):
    value=scenario(item['seed'],'clean')
    value.update(version='hard-cases-v1',level='shared_light_layout')
    value['profile'].update(xy_m=LAYOUT_XY,yaw_degrees=LAYOUT_YAW)
    rng=np.random.default_rng(np.random.SeedSequence([item['seed'],931]))
    positions,rejected=layout(rng,value['profile'])
    for body,xy in zip(value['bodies'].values(),positions):
        body.update(xy=xy,yaw_delta=float(np.radians(rng.uniform(-LAYOUT_YAW,LAYOUT_YAW))))
    value['layout_rejections']=rejected
    return value


def is_smoke(item):
    return item['seed']==SEEDS[0]
