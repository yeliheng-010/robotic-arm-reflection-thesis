"""独立冻结版本；不可覆盖结果，状态更新单独使用原子写。"""
import json
from pathlib import Path
from f_common import read, save, sha

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
METHODS = ('fixed_rule', 'direct', 'diagnostic')
SEEDS = (962301, 962302)
MAX_ATTEMPTS = 3
MAX_OBSERVATIONS = 2
MAX_DECISIONS = 4
PORT = 39116


def status(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def verify():
    manifest = read(ROOT/'manifest.json')
    for path, digest in manifest['identities'].items():
        assert sha(path) == digest, path
    return manifest
