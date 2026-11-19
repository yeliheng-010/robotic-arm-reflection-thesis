"""独立版本预算和冻结证据。"""
from pathlib import Path
from cc_common import read, save, sha, verify

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
SOURCE = PARENT/'qualification_strategy_v1/actual'
RUN = ROOT/'probe'


def current(name):
    manifest = verify(RUN/'manifest.json')
    return next(row for row in manifest['cases'] if row['name'] == name)
