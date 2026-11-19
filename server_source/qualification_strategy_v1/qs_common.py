"""分策略资格诊断的独立冻结范围。"""
from pathlib import Path
from cc_common import read, save, sha, verify

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
SOURCE = PARENT/'fresh_accuracy_v1/run'
RUN = ROOT/'probe'
NAMES = ('F0_964345_varied_noisy', 'F1_964345_varied_noisy', 'F1_964347_varied_noisy')


def current(name):
    manifest = verify(RUN/'manifest.json')
    return next(row for row in manifest['cases'] if row['case']['item']['id'] == name)
