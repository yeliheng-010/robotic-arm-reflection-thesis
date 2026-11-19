"""固定输入、有限搜索预算及独立新输出。"""
from pathlib import Path
from cc_common import read, save, sha, verify

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
RUN = ROOT/'search'
NAME = 'F0_964345_varied_noisy'
SOURCE = PARENT/'qualification_strategy_v1/actual/cases'/NAME
PRIOR = PARENT/'clearance_pose_v1/probe/probe'/NAME/'plan.json'
MAX_GOALS = 8
OPTIONS = dict(step=.35,max_checks=3000,max_nodes=2000,seconds=120.)


def inputs():
    case = verify(SOURCE/'result.json')['case']
    prior = read(PRIOR)
    assert all(not row['feasible'] and row['phase']=='pregrasp' for row in prior['prefixes'])
    return case, prior


def freeze():
    previous = verify(PARENT/'clearance_pose_v1/probe/manifest.json')
    paths = [SOURCE/'result.json',PRIOR,*ROOT.glob('*.py'),*ROOT.glob('*.sh'),*ROOT.glob('*.sbatch')]
    identities = dict(previous['identities'])
    identities.update({str(p):sha(p) for p in paths})
    save(RUN/'manifest.json',dict(identities=identities,options=OPTIONS,max_goals=MAX_GOALS,
        goal_selection='first 8 unique q1 in frozen prefix order',base_seed=42,
        physical_attempts=0,model_calls=0,training_updates=0))
