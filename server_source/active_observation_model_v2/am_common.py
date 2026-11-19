"""新种子四方法对照；只读依赖与模型身份一并冻结。"""
import json
from pathlib import Path
from unittest.mock import patch
from common import read, save, sha
from pilot import extract_seeds
from ap_common import verify as parent_verify
from hardstudy import design

ROOT=Path('/home/yeliheng/grasp_server/active_observation_model_v2')
PARENT=ROOT.parent
SOURCE=PARENT/'active_observation_pilot_v1'
FAILED=PARENT/'active_observation_model_v1'
SEEDS=tuple(range(940301,940307))
SMOKE_SEEDS=SEEDS[:1]
METHODS=('fixed_first','adaptive','base_current','base_history')
MODEL_METHODS=METHODS[2:]
ALIAS='qwen35-active-base'
PORT=38975
SHARDS=3
MAX_ATTEMPTS=3
MAX_EXTRA=2
MAX_PHYSICAL=10
MAX_CALLS=4
EXPECTED=24
SOURCE_TAG='active_observation_model_control'


def scenes():
    with patch.object(design,'SEEDS',SEEDS),patch.object(design,'TRAIN_SEED_COUNT',len(SEEDS)):
        rows=design.scenes()
    selected=[]
    for r in rows:
        if r['factor'] in ('grasp_bias','grasp_place'):
            key='M'+r['id'][1:]
            selected.append(dict(r,id=key,scene_id=key,pair_id=key,mechanism='active_observation',
                noise_profile={'sigma_m':0.,'missing_probability':0.}))
    return sorted(selected,key=lambda r:(r['seed'],r['id']))


def freeze():
    parent=parent_verify()
    assert read(SOURCE/'verification.json')['passed']
    sources=sorted((set(PARENT.glob('*/protocol.json'))|set(PARENT.glob('*/manifest.json')))-{ROOT/'manifest.json'})
    used=set()
    previous=read(FAILED/'manifest.json')
    assert read(FAILED/'STATUS.json')['status']=='failed'
    assert previous['scenes']==scenes(),'Recovery must retain all original conditions'
    for p in sources:
        if p!=FAILED/'manifest.json':
            used.update(extract_seeds(read(p)))
    assert not set(SEEDS)&used,'Seed overlap'
    files=set(ROOT.glob('*.py'))|set(ROOT.glob('*.sbatch'))|{ROOT/'environment.sh',ROOT/'PROTOCOL.md'}
    files.update(Path(p) for p in parent['identities'])
    files.update(sources)
    files.add(SOURCE/'verification.json')
    files.add(FAILED/'STATUS.json')
    files.update(Path(p) for p in previous['identities'])
    for p,expected in previous['identities'].items():
        assert sha(p)==expected,'Failed version changed: '+p
    files.add(PARENT/'set_sft_v1/eval.json')
    files.update((PARENT/'set_sft_v1/evaluation/before').glob('shard_*/result.json'))
    rows=scenes()
    assert len(rows)==EXPECTED and all(s['split']=='train_candidate' for s in rows)
    value=dict(scenes=rows,seeds=list(SEEDS),methods=list(METHODS),physical_budget=EXPECTED*MAX_PHYSICAL,
        model_call_budget=EXPECTED*len(MODEL_METHODS)*MAX_CALLS,old_seed_count=len(used),
        source=SOURCE_TAG,model=ALIAS,test_used=False,training_approved=False,
        recovery_of=dict(manifest=str(FAILED/'manifest.json'),sha256=sha(FAILED/'manifest.json'),
            reason='Successful execution has feedback=None; preserve and rerun all conditions',same_conditions=True),
        identities={str(p):sha(p) for p in sorted(files)})
    with (ROOT/'manifest.json').open('x') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)
    return value


def verify():
    value=read(ROOT/'manifest.json')
    for p,expected in value['identities'].items():
        assert Path(p).is_absolute() and sha(p)==expected,'Frozen source changed: '+p
    assert value['scenes']==scenes() and value['methods']==list(METHODS)
    assert value['physical_budget']==EXPECTED*MAX_PHYSICAL
    assert value['model_call_budget']==EXPECTED*len(MODEL_METHODS)*MAX_CALLS
    assert not value['test_used'] and not value['training_approved']
    return value


def identity():
    return dict(experiment_sha256=sha(ROOT/'manifest.json'),
        runtime_manifest_sha256=sha(PARENT/'candidate_sft_v2/manifest.json'),
        base='Qwen3.5-4B',adapter_enabled=False)


if __name__=='__main__':
    print(dict(frozen_conditions=len(freeze()['scenes'])))
