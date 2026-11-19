"""任务准确度试验独立路径，复用排他写入和身份核验。"""
from pathlib import Path
from cc_common import read, save, sha, verify

ROOT = Path(__file__).resolve().parent
PILOT = ROOT/'pilot'
SOURCE = ROOT.parent/'camera_collection_v1/pilot'
SEEDS = (964008, 964009, 964012, 964294, 964306)


def current(seed):
    manifest = verify(PILOT/'manifest.json')
    case = next(c for c in manifest['cases'] if c['item']['seed'] == seed)
    return case, manifest['references'][str(seed)]
