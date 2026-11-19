"""独立运行身份与无副作用的共享IO。"""
import hashlib
import json
from pathlib import Path

ROOT=Path('/home/yeliheng/grasp_server/recovery_diagnostic_v1')
PARENT=ROOT.parent
SFT=PARENT/'candidate_sft_v2'
NEW_SFT=PARENT/'set_sft_v1'
PREVIOUS=PARENT/'set_closed_loop_v2'
PORT=38963
METHODS=('rule','base','previous159','new189')
ALIASES={method:'qwen35-candidate-'+method for method in METHODS if method!='rule'}
EXPECTED=24
SMOKE_EXPECTED=8
SHARDS=3
SCENES=('H0_920018_grasp_place','H1_920017_grasp_collision',
        'H1_920019_grasp_collision','H1_920019_grasp_place')
MISSING_SCENES=('H0_920018_grasp_place','H1_920019_grasp_place')


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
    return entry['item']['scene_id']==SCENES[0]


def verify():
    manifest=read(ROOT/'manifest.json')
    for path,expected in manifest['identities'].items():
        assert Path(path).is_absolute(),'Relative identity path rejected: '+path
        assert sha(path)==expected,'Frozen identity changed: '+path
    assert len(manifest['entries'])==EXPECTED and manifest['max_physical']==88
    parents={e['uid']:e for e in read(PREVIOUS/'manifest.json')['entries']}
    assert len({e['uid'] for e in manifest['entries']})==EXPECTED
    for entry in manifest['entries']:
        item=entry['item']
        assert entry['method'] in METHODS and item['split']=='development_validation'
        source=parents[entry['source_uid']]
        assert item==source['item'] and entry['method']==source['method']
        assert item['arm']==('new_rule' if entry['method']=='rule' else 'hybrid')
        assert entry['uid']==entry['source_uid']+'__'+entry['variant']
        assert entry['package']=='hardstudy' and entry['batch']=='hard_cases_v1'
        assert entry['eligible'] and source['eligible']
        assert entry['variant'] in ('budget4','no_missing')
        allowed=SCENES if entry['variant']=='budget4' else MISSING_SCENES
        assert item['scene_id'] in allowed
        assert entry['max_attempts']==(4 if entry['variant']=='budget4' else 3)
    assert sum(e['max_attempts'] for e in manifest['entries'])==88
    assert sum(is_smoke(e) for e in manifest['entries'])==SMOKE_EXPECTED
    assert len({e['item']['scene_id'] for e in manifest['entries']})==4
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
