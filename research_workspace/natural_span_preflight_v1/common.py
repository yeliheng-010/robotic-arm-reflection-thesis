from pathlib import Path
from f_common import read, save, sha

ROOT = Path(__file__).resolve().parent
SEEDS = tuple(range(963001, 963013))
MIN_PIXELS = 64
MIN_FRACTION = .70


def visible(row):
    return row['pixels'] >= MIN_PIXELS and row['visible_fraction'] >= MIN_FRACTION


def verify():
    manifest = read(ROOT/'manifest.json')
    assert all(sha(p) == h for p, h in manifest['identities'].items())
    return manifest
