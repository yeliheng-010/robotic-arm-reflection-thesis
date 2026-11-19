import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
SOURCE = PROJECT/'model_grasp_gpu_v3'
QUALIFIED = PROJECT/'qualification_strategy_v1/actual/cases/F1_964347_varied_noisy'
MAX_ACTIONS = 738
ENDPOINT_SECONDS = 300
PATH_SECONDS = 120


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)


def verify():
    manifest = read(ROOT/'manifest.json')
    assert manifest['max_actions']==MAX_ACTIONS and manifest['model_calls']==0
    assert manifest['physical_attempts']==0 and manifest['max_path_actions']==4
    for name,digest in manifest['identities'].items():
        assert sha(name)==digest,name
    return manifest
