from pathlib import Path
from qualified_model_v1.common import read, save, sha

ROOT = Path(__file__).resolve().parent
PROJECT, RUN = ROOT.parent, ROOT/'run'
SEED = 978505
SOURCE = PROJECT/f'qualified_joint_feedback_v1/run/{SEED}/decision_1'
NUMERIC_ATOL = 1e-12
SETTLE_STEPS = 250


def verify():
    manifest = read(RUN/'manifest.json')
    assert all(sha(p) == h for p, h in manifest['identities'].items())
    return manifest


def case():
    return read(PROJECT/'qualified_task_v1/run/manifest.json')['cases'][str(SEED)]


def plan():
    return read(SOURCE/'private_plan.json')['plan']
