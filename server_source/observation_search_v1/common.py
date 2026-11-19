from pathlib import Path
from surface_grasp_v1.common import read, save, sha
from pose_fresh_v1.common import files, contains_seed

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
RUN = ROOT / 'run'
SEEDS = tuple(range(978501, 978513))
METHODS = ('joint', 'adaptive')
NOISE_PREFIX = 978901
GLOBAL_BUDGET = 128
ROUNDS = 4
ROUND_BUDGET = 32


def verify():
    manifest = read(RUN / 'manifest.json')
    for name, digest in manifest['identities'].items():
        assert sha(name) == digest, name
    return manifest
