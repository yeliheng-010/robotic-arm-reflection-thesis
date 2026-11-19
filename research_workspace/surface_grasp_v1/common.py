import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)


def verify():
    manifest=read(ROOT/'manifest.json')
    assert manifest['max_candidates']==512 and manifest['max_path_actions']==4
    assert manifest['model_calls']==manifest['physical_attempts']==0
    for name,digest in manifest['identities'].items():
        assert sha(name)==digest,name
    return manifest
