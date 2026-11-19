from pathlib import Path
from sd_common import read, sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'scene_pair_collision_v1'


def verify():
    manifest = read(ROOT/'manifest.json')
    assert read(ROOT/'preflight.json')['manifest_sha256'] == sha(ROOT/'manifest.json')
    for path, digest in manifest['identities'].items():
        assert sha(path) == digest, 'Frozen identity changed: '+path
    return manifest
