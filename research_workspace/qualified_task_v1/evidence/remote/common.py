from pathlib import Path
from surface_grasp_v1.common import read, save, sha

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
RUN = ROOT/'run'
SEEDS = (978501, 978505, 978506, 978507, 978510, 978512)
PILOT = SEEDS[:2]


def verify():
    value = read(RUN/'manifest.json')
    for name, digest in value['identities'].items():
        assert sha(name) == digest, name
    return value
