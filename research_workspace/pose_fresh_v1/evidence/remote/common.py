"""新队列的独占输出与只读来源校验。"""
from pathlib import Path
from surface_grasp_v1.common import read, save, sha

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
RUN = ROOT / 'run'


def verify():
    manifest = read(RUN / 'manifest.json')
    for name, digest in manifest['identities'].items():
        assert sha(name) == digest, name
    return manifest


def files(folder):
    return {str(path.relative_to(folder)): sha(path)
            for path in sorted(folder.rglob('*')) if path.is_file()}


def contains_seed(value, seeds):
    if isinstance(value, dict):
        return any(contains_seed(v, seeds) for v in value.values())
    if isinstance(value, list):
        return any(contains_seed(v, seeds) for v in value)
    return type(value) is int and value in seeds
