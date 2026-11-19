"""固定预算、独立输出以及排他创建。"""
from pathlib import Path
from cc_common import read, save, sha, verify

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
RUN = ROOT/'run'
SEEDS = (964345, 964346, 964347, 964348)
POLICIES = ('original', 'improved')


def base(name, policy):
    assert policy in POLICIES
    assert name in {c['item']['id'] for c in read(RUN/'manifest.json')['cases']}
    return RUN/'conditions'/name/policy


def case_at(folder):
    return verify(folder/'manifest.json')['cases'][0]
