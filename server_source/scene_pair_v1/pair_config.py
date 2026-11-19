"""当前仅有原配置、全部变化加噪声两种场景。"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PREDECESSOR = ROOT.parent/'scene_diversity_v2'/'manifest.json'
PREDECESSOR_SHA256 = '87e95193a675bf2e95057ba4b0b87a307544d50425a19b6f9815ac92b1ddb512'
SCENES = ('baseline', 'varied_noisy')
DEFAULT_SEED = 960102
PAIRS = (('RedBlock', 'BlueBin'), ('PurpleCapsule', 'RedBin'))
NOISE_SIGMA_M = .003
NOISE_DROPOUT = .02


def configuration(seed, scene):
    if scene not in SCENES or type(seed) is not int:
        raise ValueError('Expected baseline or varied_noisy and an integer seed')
    raw = PREDECESSOR.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PREDECESSOR_SHA256:
        raise ValueError('Frozen scene source identity changed')
    manifest = json.loads(raw)
    if seed not in manifest['seeds']:
        raise ValueError('Use an existing development seed from 960101 to 960112')
    previous = 'baseline' if scene == 'baseline' else 'combined'
    config = deepcopy(manifest['configs'][f'{seed}_{previous}'])
    active = scene == 'varied_noisy'
    config.update(group=scene, sensor=dict(depth_sigma_m=NOISE_SIGMA_M if active else 0.,
                                         dropout=NOISE_DROPOUT if active else 0.))
    return config


def item(seed, scene, *, source, destination):
    if (source, destination) not in PAIRS:
        raise ValueError('Only existing non-heldout development task pairs are supported')
    configuration(seed, scene)
    return dict(id=f'{scene}_{seed}_{source}_{destination}', seed=seed, group=scene,
                source=source, destination=destination, fault='none',
                split='development_integration', model_calls=0, test_used=False)
