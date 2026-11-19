"""本轮独立身份与全量记账。"""
from pathlib import Path
from rc_common import read, save, sha

PARENT = Path('/home/yeliheng/grasp_server')
ROOT = PARENT/'container_motion_v1'
DIAGNOSTIC = PARENT/'container_decision_diagnostic_v1'
LAYOUT = PARENT/'container_layout_v2'
SEEDS = tuple(range(950501,950541))
PAIRS = (('RedBlock','BlueBin'),('PurpleCapsule','RedBin'))
SHARDS = 4
METHODS = ('rule','geometry')


def verify():
    value = read(ROOT/'manifest.json')
    for path,digest in value['identities'].items():
        assert sha(path)==digest, 'Frozen source changed: '+path
    assert value['seeds']==list(SEEDS) and len(value['cases'])==11
    assert not value['test_used'] and not value['training_approved']
    return value


def gate(name):
    value = read(ROOT/name)
    assert value['passed'] and value['manifest_sha256']==sha(ROOT/'manifest.json')
    return value


def validation_items():
    return [dict(id=f'M{pair}_{seed}_randomized',source=src,destination=dst,
        seed=seed,arm='randomized',split='new_seed_development_validation',fault='none')
        for seed in SEEDS for pair,(src,dst) in enumerate(PAIRS)]
