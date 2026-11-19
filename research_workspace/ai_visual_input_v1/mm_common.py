from pathlib import Path
from f_common import read, save, sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'ai_route_bridge_v2'
CASE = 'V0_962501_varied_noisy'


def verify():
    value = read(ROOT/'manifest.json')
    assert all(sha(p) == h for p, h in value['identities'].items())
    return value
