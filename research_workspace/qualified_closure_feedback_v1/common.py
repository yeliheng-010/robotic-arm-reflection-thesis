from pathlib import Path
from qualified_model_v1.common import read, save, sha

ROOT = Path(__file__).resolve().parent
PROJECT, RUN = ROOT.parent, ROOT / 'run'
SEED = 978505
MAX_DECISIONS = 2


def verify():
    manifest = read(RUN / 'manifest.json')
    for name, digest in manifest['identities'].items():
        assert sha(name) == digest, name
    return manifest
