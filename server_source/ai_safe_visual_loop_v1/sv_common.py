from pathlib import Path
from f_common import read, save, sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'safe_visual_preflight_v1'
PORT = 39128
METHODS = ('fixed_rule', 'direct', 'diagnostic')


def verify():
    manifest = read(ROOT/'manifest.json')
    assert all(sha(p) == h for p, h in manifest['identities'].items())
    return manifest
