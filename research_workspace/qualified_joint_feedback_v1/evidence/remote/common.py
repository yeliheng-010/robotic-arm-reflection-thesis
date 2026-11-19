from pathlib import Path
from qualified_model_v1.common import read, save, sha

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
RUN = ROOT/'run'
SEEDS = (978501, 978505)
MAX_DECISIONS = 2


def verify():
    manifest = read(RUN/'manifest.json')
    assert all(sha(p) == h for p, h in manifest['identities'].items())
    return manifest
