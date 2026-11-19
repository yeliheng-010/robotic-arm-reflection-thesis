"""单次完整任务验证，使用原顶面抓取和新的归位规划。"""
import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import cc_worker
from cc_common import verify
from rh_prepare import REPAIR
from rh_runtime import ReturnSession


if __name__ == '__main__':
    seed = int(sys.argv[1])
    manifest = verify(REPAIR/'manifest.json')
    case = next(c for c in manifest['cases'] if c['item']['seed'] == seed)
    with patch.object(cc_worker, 'PILOT', REPAIR), patch.object(cc_worker, 'VisibleSession', ReturnSession):
        cc_worker.execute(case)
