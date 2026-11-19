from pathlib import Path
from surface_grasp_v1.common import read,save,sha
from surface_physical_v1.common import verify

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
TRIAL=ROOT/'trial'
PHASES={'preflight':0,'after_lift':1,'before_release':2}
CAMERA_BUDGET=32
MIN_VIEW_ANGLE_DEG=10.


def registered():
    return verify(TRIAL/'manifest.json')
