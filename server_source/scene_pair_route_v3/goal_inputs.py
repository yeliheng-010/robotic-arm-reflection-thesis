from pathlib import Path
from sd_common import read,sha

ROOT=Path(__file__).resolve().parent
PREVIOUS=ROOT.parent/'scene_pair_route_v2'


def inputs():
    manifest=read(PREVIOUS/'manifest.json')
    for path,digest in manifest['identities'].items():
        assert sha(path)==digest,path
    verification=read(PREVIOUS/'verification.json')
    assert verification['passed'] and verification['actual_new_attempts']==0
    assert verification['manifest_sha256']==sha(PREVIOUS/'manifest.json')
    for case in manifest['cases']:
        for step in case['steps']:
            assert sha(step['result_path'])==step['result_sha256']
    return manifest['cases']
