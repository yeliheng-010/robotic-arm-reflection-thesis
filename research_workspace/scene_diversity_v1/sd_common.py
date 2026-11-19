"""新实验自身文件身份与写入边界。"""
import hashlib
import json
from pathlib import Path
from sd_config import ROOT


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify():
    manifest = read(ROOT/'manifest.json')
    assert read(ROOT/'preflight.json')['manifest_sha256']==sha(ROOT/'manifest.json')
    for name, digest in manifest['identities'].items():
        if sha(name) != digest:
            raise ValueError('Frozen source changed: '+name)
    return manifest


def config_for(item, manifest):
    return manifest['configs'][str(item['seed'])+'_'+item['group']]
