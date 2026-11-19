"""相机资格实验身份与固定预算。"""
from pathlib import Path
from sd_common import read, sha

ROOT = Path(__file__).resolve().parent
SHARDS = 4


def verify_source():
    folder = ROOT.parent/'scene_pair_feasibility_v2'
    digest = sha(folder/'manifest.json')
    assert read(folder/'preflight.json')['manifest_sha256'] == digest
    for path, expected in read(folder/'manifest.json')['identities'].items():
        assert sha(path) == expected, 'Frozen source changed: '+path
    return digest


def verify():
    manifest = read(ROOT/'manifest.json')
    assert read(ROOT/'preflight.json')['manifest_sha256'] == sha(ROOT/'manifest.json')
    for path, digest in manifest['identities'].items():
        assert sha(path) == digest, 'Frozen source changed: '+path
    assert {row['group'] for row in manifest['items']} == {'baseline', 'varied_noisy'}
    assert len(manifest['items']) == 48 and len({r['id'] for r in manifest['items']}) == 48
    assert set(manifest['configs']) == {r['id'] for r in manifest['items']}
    return manifest


def enhanced(manifest):
    return [row for row in manifest['items'] if row['group'] == 'varied_noisy']
