from pathlib import Path
from f_common import read, save, sha

ROOT = Path(__file__).resolve().parent
PORT = 39127
CONDITIONS = ('C0_962703_varied_noisy', 'C1_962708_varied_noisy')


def verify():
    manifest = read(ROOT/'manifest.json')
    assert all(sha(p) == h for p, h in manifest['identities'].items())
    return manifest
