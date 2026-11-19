"""冻结身份、实验条目与共享IO；训练权重仅用于服务身份回放。"""
import hashlib
import json
from pathlib import Path

ROOT=Path('/home/yeliheng/grasp_server/framework_ablation_v1')
PARENT=ROOT.parent
SFT=PARENT/'candidate_sft_v2'
NEW_SFT=PARENT/'set_sft_v1'
PORT=38964
METHODS=('retry','rule','current','history')
ALIASES={m:'qwen35-candidate-'+m for m in ('base','previous159','new189')}
BUDGETS=(3,4)
EXPECTED=480
SMOKE_EXPECTED=48
SHARDS=3
ARMS={'retry':'new_rule','rule':'new_rule','current':'hybrid','history':'hybrid'}


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):
            value.update(block)
    return value.hexdigest()


def save(path,value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    temporary.replace(path)


def is_smoke(entry):
    i=entry['item']
    return entry['max_attempts']==3 and (
        entry['batch']=='scene_expansion_v1' and i['seed']==910009 and i['factor']=='combined'
        or entry['batch']=='hard_cases_v1' and i['seed']==920017)


def in_phase(entry,phase):
    if phase=='smoke':
        return is_smoke(entry)
    return entry['max_attempts']==(3 if phase in ('batch3','primary') else 4)


def verify():
    manifest=read(ROOT/'manifest.json')
    for path,expected in manifest['identities'].items():
        assert Path(path).is_absolute() and sha(path)==expected,'Frozen identity changed: '+path
    entries=manifest['entries']
    assert len(entries)==EXPECTED and len({e['uid'] for e in entries})==EXPECTED
    parents={b:{i['id']:i for i in read(PARENT/b/'protocol.json')['items']}
             for b in ('scene_expansion_v1','hard_cases_v1')}
    for e in entries:
        i=e['item']
        assert e['method'] in METHODS and e['max_attempts'] in BUDGETS
        assert i==parents[e['batch']][i['id']] and i['split']=='development_validation'
        assert i['arm']==ARMS[e['method']]
        assert e['uid']==f"b{e['max_attempts']}__{i['scene_id']}__{e['method']}"
        assert e['package']==('expand' if e['batch']=='scene_expansion_v1' else 'hardstudy')
    assert len({e['item']['scene_id'] for e in entries})==60
    assert sum(is_smoke(e) for e in entries)==SMOKE_EXPECTED
    return manifest


def model_identity():
    return dict(experiment_sha256=sha(ROOT/'manifest.json'),
                training_manifests={m:sha(p/'manifest.json') for m,p in
                                    (('previous159',SFT),('new189',NEW_SFT))},
                adapter_sha256={m:read(p/'training/result.json')['adapter_files']['adapter_model.safetensors']
                                for m,p in (('previous159',SFT),('new189',NEW_SFT))})


def requested_adapter(method):
    assert method in ALIASES
    return None if method=='base' else model_identity()['adapter_sha256'][method]
