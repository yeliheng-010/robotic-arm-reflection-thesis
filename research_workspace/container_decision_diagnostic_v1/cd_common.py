"""独立诊断身份；不向旧实验写入。"""
from pathlib import Path
from rc_common import read, save, sha

PARENT = Path('/home/yeliheng/grasp_server')
ROOT = PARENT/'container_decision_diagnostic_v1'
SOURCE = PARENT/'container_recovery_v2'
LAYOUT = PARENT/'container_layout_v2'
ALIAS = 'qwen35-container-recovery-base'
SHARDS = 4
VARIANTS = ('replay', 'reverse', 'summary', 'expert_hint')
HEIGHTS = (.20, .25, .30)


def verify():
    manifest = read(ROOT/'manifest.json')
    for path, digest in manifest['identities'].items():
        assert sha(path) == digest, 'Frozen source changed: '+path
    assert len(manifest['cases']) == 11 and len(manifest['branches']) == 73
    assert not manifest['test_used'] and not manifest['training_approved']
    return manifest


def identity():
    return dict(experiment_sha256=sha(ROOT/'manifest.json'),
        runtime_manifest_sha256=sha(PARENT/'candidate_sft_v2/manifest.json'),
        base='Qwen3.5-4B', adapter_enabled=False)


def gate(name):
    value = read(ROOT/name)
    assert value['passed'] and value['manifest_sha256'] == sha(ROOT/'manifest.json')
    return value
