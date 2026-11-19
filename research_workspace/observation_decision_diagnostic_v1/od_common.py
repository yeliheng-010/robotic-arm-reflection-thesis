"""冻结旧来源与新诊断，复用开发快照而不声称新增独立样本。"""
import json
from pathlib import Path
from common import read,save,sha
from am_common import verify as parent_verify

ROOT=Path('/home/yeliheng/grasp_server/observation_decision_diagnostic_v1')
PARENT=ROOT.parent
SOURCE=PARENT/'active_observation_model_v2'
ALIAS='qwen35-observation-diagnostic-base'
LEVELS=(0,1,2)
SELECTORS=('rule','model')
SHARDS=4
SMOKE_CASES=4
MAX_CALLS=402
MAX_PHYSICAL=66


def freeze():
    from od_source import inventory
    parent=parent_verify()
    final=read(SOURCE/'verification.json')
    assert final['passed'] and final['complete'] and final['accounted']==24
    data=inventory()
    files=set(ROOT.glob('*.py'))|set(ROOT.glob('*.sbatch'))|{ROOT/'PROTOCOL.md',ROOT/'environment.sh'}
    files.update(Path(p) for p in parent['identities'])
    files.update(SOURCE.rglob('*.json'))
    value=dict(**data,source='observation_decision_diagnostic',source_manifest_sha256=sha(SOURCE/'manifest.json'),
        source_seeds=parent['seeds'],model_call_budget=MAX_CALLS,physical_budget=MAX_PHYSICAL,
        levels=list(LEVELS),selectors=list(SELECTORS),test_used=False,training_approved=False,
        independent_new_samples=False,identities={str(p):sha(p) for p in sorted(files)})
    with (ROOT/'manifest.json').open('x') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)
    return value


def verify():
    value=read(ROOT/'manifest.json')
    for p,expected in value['identities'].items():
        assert Path(p).is_absolute() and sha(p)==expected,'Frozen source changed: '+p
    assert len(value['rows'])==82 and len(value['cases'])==11
    assert value['model_call_budget']==MAX_CALLS and value['physical_budget']==MAX_PHYSICAL
    assert value['levels']==list(LEVELS) and value['selectors']==list(SELECTORS)
    assert not value['test_used'] and not value['training_approved']
    return value


def identity():
    return dict(experiment_sha256=sha(ROOT/'manifest.json'),
        runtime_manifest_sha256=sha(PARENT/'candidate_sft_v2/manifest.json'),
        base='Qwen3.5-4B',adapter_enabled=False)


if __name__=='__main__':
    value=freeze()
    print(dict(source_conditions=24,decisions=len(value['rows']),missing_snapshots=len(value['cases'])))
