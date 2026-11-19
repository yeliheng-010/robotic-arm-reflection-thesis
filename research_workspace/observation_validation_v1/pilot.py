"""新训练条件、冻结身份和严格计费上限。"""
import json
from pathlib import Path
from unittest.mock import patch
from common import verify as verify_parent,read,save,sha
from hardstudy import design

ROOT=Path('/home/yeliheng/grasp_server/observation_validation_v1')
SEEDS=tuple(range(940101,940113))
SMOKE_SEEDS=SEEDS[:2]
SHARDS=4
MECHANISMS={'outlier':'grasp_bias'}
EXPECTED=24
PHYSICAL_BUDGET=144
MAX_PHYSICAL={'occlusion':6,'outlier':6,'side_effect':8}
MAX_ATTEMPTS={'occlusion':3,'outlier':3,'side_effect':4}
MAX_EXTRA=2


def scenes():
    with patch.object(design,'SEEDS',SEEDS),patch.object(design,'TRAIN_SEED_COUNT',len(SEEDS)):
        original=design.scenes()
    rows=[]
    for mechanism,family in MECHANISMS.items():
        for row in original:
            if row['factor']!=family:
                continue
            key='V'+row['id'][1:]+'_'+mechanism
            rows.append(dict(row,id=key,scene_id=key,pair_id=key,mechanism=mechanism,
                             noise_profile=dict(sigma_m=.005,missing_probability=0.)))
    return sorted(rows,key=lambda r:(r['seed'],r['id']))


def extract_seeds(value):
    result=set()
    if isinstance(value,dict):
        for k,v in value.items():
            if k=='seed' and type(v) is int:
                result.add(v)
            elif k.endswith('seeds') and isinstance(v,list):
                result.update(s for s in v if type(s) is int)
            elif isinstance(v,(dict,list)):
                result.update(extract_seeds(v))
    elif isinstance(value,list):
        for v in value:
            result.update(extract_seeds(v))
    return result


def seed_sources():
    paths=set(ROOT.parent.glob('*/protocol.json'))|set(ROOT.parent.glob('*/manifest.json'))
    return sorted(p for p in paths if p.parent!=ROOT)


def freeze():
    parent=verify_parent()
    used=set()
    sources=seed_sources()
    for path in sources:
        used.update(extract_seeds(read(path)))
    assert not set(SEEDS)&used,'New seeds overlap registered sources'
    files=list(ROOT.glob('*.py'))+list(ROOT.glob('*.sbatch'))+[ROOT/'environment.sh',ROOT/'PROTOCOL.md']
    files+=sources+[ROOT.parent/'framework_ablation_v1/manifest.json']
    files+=[Path(p) for p in parent['identities']]
    rows=scenes()
    assert len(rows)==EXPECTED and all(s['split']=='train_candidate' for s in rows)
    value=dict(scenes=rows,seeds=list(SEEDS),old_seed_count=len(used),seed_sources=[str(p) for p in sources],
        physical_budget=PHYSICAL_BUDGET,budgets=[1,2,3],smoke_seeds=list(SMOKE_SEEDS),
        source='synthetic_sensor_rule_qualification',model=None,test_used=False,
        identities={str(p):sha(p) for p in sorted(set(files))})
    with (ROOT/'manifest.json').open('x') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)
    return value


def verify():
    value=read(ROOT/'manifest.json')
    for path,expected in value['identities'].items():
        assert Path(path).is_absolute() and sha(path)==expected,'Frozen source changed: '+path
    assert value['scenes']==scenes() and value['physical_budget']==PHYSICAL_BUDGET
    assert value['budgets']==[1,2,3] and value['smoke_seeds']==list(SMOKE_SEEDS)
    used=set()
    for path in value['seed_sources']:
        used.update(extract_seeds(read(path)))
    assert not set(SEEDS)&used
    return value


if __name__=='__main__':
    print(dict(conditions=len(freeze()['scenes']),physical_budget=PHYSICAL_BUDGET))
