"""独立实验身份；父目录只读，任务模型固定基础4B。"""
import json
from pathlib import Path
from common import read,save,sha
from pilot import verify as parent_verify

ROOT=Path('/home/yeliheng/grasp_server/observation_model_control_v1')
PARENT=ROOT.parent
SOURCE=PARENT/'observation_validation_v1'
SFT=PARENT/'candidate_sft_v2'
NEW_SFT=PARENT/'set_sft_v1'
PORT=38974
METHODS=('rule_latest','rule_median','base_latest','base_median')
ALIASES={m:'qwen35-candidate-'+m for m in ('base','previous159','new189')}
SHARDS=3
SMOKE_SEEDS=(940101,940102)
MAX_ATTEMPTS=3
MAX_EXTRA=2
MAX_PHYSICAL=10


def freeze():
    parent=parent_verify()
    assert read(SOURCE/'final_verification.json')['passed']
    files=set(ROOT.glob('*.py'))|set(ROOT.glob('*.sbatch'))|{ROOT/'environment.sh',ROOT/'PROTOCOL.md'}
    files.update(Path(p) for p in parent['identities'])
    files.update([SOURCE/'manifest.json',SOURCE/'final_verification.json'])
    for folder in ('tasks','qualification'):
        files.update((SOURCE/folder).rglob('*.json'))
    value=dict(scenes=parent['scenes'],methods=list(METHODS),budgets=[1,2,3],conditions=24,
        trajectories=96,physical_budget=240,model_call_budget=96,test_used=False,training_approved=False,
        source='observation_processing_selector_control',model='Qwen3.5-4B-base-adapter-disabled',
        identities={str(p):sha(p) for p in sorted(files)})
    with (ROOT/'manifest.json').open('x') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)
    return value


def verify():
    value=read(ROOT/'manifest.json')
    for path,expected in value['identities'].items():
        assert Path(path).is_absolute() and sha(path)==expected,'Frozen source changed: '+path
    assert value['scenes']==read(SOURCE/'manifest.json')['scenes']
    assert len(value['scenes'])==24 and value['methods']==list(METHODS)
    assert value['budgets']==[1,2,3] and value['physical_budget']==240 and value['model_call_budget']==96
    assert not value['test_used'] and not value['training_approved']
    return value


def model_identity():
    return dict(experiment_sha256=sha(ROOT/'manifest.json'),
        training_manifests={m:sha(p/'manifest.json') for m,p in (('previous159',SFT),('new189',NEW_SFT))},
        adapter_sha256={m:read(p/'training/result.json')['adapter_files']['adapter_model.safetensors']
                       for m,p in (('previous159',SFT),('new189',NEW_SFT))})


def requested_adapter(method):
    assert method in ALIASES
    return None if method=='base' else model_identity()['adapter_sha256'][method]


if __name__=='__main__':
    print(dict(frozen_conditions=len(freeze()['scenes'])))
