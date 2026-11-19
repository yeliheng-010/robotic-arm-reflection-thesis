"""新种子主动观测资格试验；独立冻结与有限预算。"""
import json
from pathlib import Path
from unittest.mock import patch
from common import read,save,sha
from pilot import extract_seeds
from om_common import verify as parent_verify
from hardstudy import design

ROOT=Path('/home/yeliheng/grasp_server/active_observation_pilot_v1')
PARENT=ROOT.parent
SOURCE=PARENT/'observation_model_control_v1'
SEEDS=tuple(range(940201,940207))
SMOKE_SEEDS=SEEDS[:1]
METHODS=('fixed_first','adaptive')
FAMILIES=('grasp_bias','grasp_place')
SHARDS=4
MAX_ATTEMPTS=3
MAX_EXTRA=2
MAX_PHYSICAL=6
EXPECTED=24


def scenes():
    with patch.object(design,'SEEDS',SEEDS),patch.object(design,'TRAIN_SEED_COUNT',len(SEEDS)):
        rows=design.scenes()
    out=[]
    for row in rows:
        if row['factor'] not in FAMILIES:
            continue
        key='A'+row['id'][1:]
        out.append(dict(row,id=key,scene_id=key,pair_id=key,mechanism='active_observation',
                        noise_profile={'sigma_m':0.,'missing_probability':0.}))
    return sorted(out,key=lambda r:(r['seed'],r['id']))


def freeze():
    parent=parent_verify()
    sources=sorted((set(PARENT.glob('*/protocol.json'))|set(PARENT.glob('*/manifest.json')))-{ROOT/'manifest.json'})
    used=set()
    for path in sources:
        used.update(extract_seeds(read(path)))
    assert not set(SEEDS)&used,'Seed overlap'
    files=set(ROOT.glob('*.py'))|set(ROOT.glob('*.sbatch'))|{ROOT/'environment.sh',ROOT/'PROTOCOL.md'}
    files.update(Path(p) for p in parent['identities'])
    files.update(sources)
    files.add(SOURCE/'manifest.json')
    rows=scenes()
    assert len(rows)==EXPECTED and all(s['split']=='train_candidate' for s in rows)
    value=dict(scenes=rows,seeds=list(SEEDS),methods=list(METHODS),budgets=[1,2,3],
        physical_budget=EXPECTED*MAX_PHYSICAL,old_seed_count=len(used),seed_sources=[str(p) for p in sources],
        source='active_observation_rule_qualification',model=None,test_used=False,training_approved=False,
        identities={str(p):sha(p) for p in sorted(files)})
    with (ROOT/'manifest.json').open('x') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)
    return value


def verify():
    value=read(ROOT/'manifest.json')
    for path,expected in value['identities'].items():
        assert Path(path).is_absolute() and sha(path)==expected,'Frozen source changed: '+path
    assert value['scenes']==scenes() and value['methods']==list(METHODS)
    assert value['budgets']==[1,2,3] and value['physical_budget']==EXPECTED*MAX_PHYSICAL
    return value


if __name__=='__main__':
    print(dict(frozen_conditions=len(freeze()['scenes'])))
