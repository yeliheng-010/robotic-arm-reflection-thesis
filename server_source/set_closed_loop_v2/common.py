"""独立运行身份与无副作用的共享IO。"""
import hashlib
import json
from pathlib import Path

ROOT=Path('/home/yeliheng/grasp_server/set_closed_loop_v2')
PARENT=ROOT.parent
SFT=PARENT/'candidate_sft_v2'
NEW_SFT=PARENT/'set_sft_v1'
PORT=38962
METHODS=('rule','base','previous159','new189')
ALIASES={method:'qwen35-candidate-'+method for method in METHODS if method!='rule'}
EXPECTED=240
SMOKE_EXPECTED=48
SHARDS=3


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):
            value.update(block)
    return value.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def save(path,value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    temporary.replace(path)


def is_smoke(entry):
    i=entry['item']
    return (entry['batch']=='scene_expansion_v1' and i['seed']==910009 and i['factor']=='combined'
            or entry['batch']=='hard_cases_v1' and i['seed']==920017)


def verify():
    manifest=read(ROOT/'manifest.json')
    for path,expected in manifest['identities'].items():
        assert Path(path).is_absolute(),'Relative identity path rejected: '+path
        assert sha(path)==expected,'Frozen identity changed: '+path
    assert len(manifest['entries'])==EXPECTED and manifest['max_attempts']==3
    parents={batch:{i['id']:i for i in read(PARENT/batch/'protocol.json')['items']}
             for batch in ('scene_expansion_v1','hard_cases_v1')}
    assert len({e['uid'] for e in manifest['entries']})==EXPECTED
    for entry in manifest['entries']:
        item=entry['item']
        assert entry['method'] in METHODS and item['split']=='development_validation'
        assert item==parents[entry['batch']][item['id']]
        assert item['arm']==('new_rule' if entry['method']=='rule' else 'hybrid')
        assert entry['uid']==item['scene_id']+'__'+entry['method']
        assert entry['package']==('expand' if entry['batch']=='scene_expansion_v1' else 'hardstudy')
    assert len({e['item']['scene_id'] for e in manifest['entries']})==60
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
