"""运行身份冻结和原子状态写入。"""
import hashlib
import json
import os
from pathlib import Path
from cl_design import ROOT


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+f'.{os.getpid()}.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def verify():
    manifest = read(ROOT/'manifest.json')
    for path, digest in manifest['identities'].items():
        assert sha(path)==digest, 'Frozen file changed: '+path
    assert sha(ROOT/'plan.json')==manifest['plan_sha256']
    return read(ROOT/'plan.json')


def task(index, plan):
    item = plan['items'][index]
    return item, plan['layouts'][str(item['seed'])]
