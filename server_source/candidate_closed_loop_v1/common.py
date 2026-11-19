"""独立运行身份与无副作用的共享IO。"""
import hashlib
import json
from pathlib import Path

ROOT=Path('/home/yeliheng/grasp_server/candidate_closed_loop_v1')
PARENT=ROOT.parent
SFT=PARENT/'candidate_sft_v2'
PORT=38961
METHODS=('rule','base','tuned')
ALIASES={'base':'qwen35-candidate-base','tuned':'qwen35-candidate-tuned'}


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
        assert sha(path)==expected,'Frozen identity changed: '+path
    assert len(manifest['entries'])==180 and manifest['max_attempts']==3
    return manifest


def model_identity():
    return dict(experiment_sha256=sha(ROOT/'manifest.json'),
                training_manifest_sha256=sha(SFT/'manifest.json'),
                adapter_sha256=read(SFT/'training/result.json')['adapter_files']['adapter_model.safetensors'])
