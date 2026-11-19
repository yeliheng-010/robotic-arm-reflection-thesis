"""新采集独立存储；写入只使用排他创建。"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
PILOT = ROOT/'pilot'
SEEDS = (964008, 964009, 964012, 964294, 964306)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(path):
    value = read(path)
    for name, digest in value['identities'].items():
        if sha(name) != digest:
            raise ValueError('Frozen file changed: '+name)
    return value


def current(seed):
    manifest = verify(PILOT/'manifest.json')
    return next(c for c in manifest['cases'] if c['item']['seed'] == seed)
