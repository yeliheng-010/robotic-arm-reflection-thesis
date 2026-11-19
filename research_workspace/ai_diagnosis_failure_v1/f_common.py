"""独立版本的只读身份核验与不可覆盖产物写入。"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')


def verify():
    value = read(ROOT/'manifest.json')
    for path, digest in value['identities'].items():
        assert sha(path) == digest, path
    return value
