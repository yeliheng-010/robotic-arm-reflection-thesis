import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRAINING = ROOT.parent / 'visual_finetune_v1'
BASE = ROOT.parent / 'visual_comparison_v1'
original_paths = list(sys.path)
sys.path.insert(0, str(TRAINING))
import vf_common_v2 as common
assert Path(common.__file__).resolve().parent == TRAINING
sys.path.insert(0, str(BASE))
from vc_metrics import classify
sys.path[:] = original_paths


def lines(path):
    with path.open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def locations():
    settings = common.config()
    export = Path(settings['dataset']).name
    assert export.startswith('job_') and export[4:].isdigit()
    return ROOT / 'prepared' / ('export_' + export[4:]), BASE / 'prepared' / ('export_' + export[4:])
