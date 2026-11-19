"""两场景完整配对协议；前两次相同，仅在门控触发时分支。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEEDS = tuple(range(961101, 961113))
SCENES = ('baseline', 'varied_noisy')
PAIRS = (('RedBlock', 'BlueBin'), ('PurpleCapsule', 'RedBin'))
SHARDS = 4


def items():
    return [dict(id=f'{seed}_{scene}_{pair}', seed=seed, group=scene, source=source,
                 destination=destination, fault='none', split='new_seed_development_validation')
            for seed in SEEDS for scene in SCENES
            for pair, (source, destination) in enumerate(PAIRS)]


def verify():
    from sd_common import read, sha
    manifest = read(ROOT/'manifest.json')
    assert read(ROOT/'preflight.json')['manifest_sha256'] == sha(ROOT/'manifest.json')
    assert manifest['items'] == items() and manifest['seeds'] == list(SEEDS)
    for path, digest in manifest['identities'].items():
        assert sha(path) == digest, 'Frozen source changed: '+path
    return manifest
