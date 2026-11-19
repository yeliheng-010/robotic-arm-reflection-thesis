"""固定同一首轮预算，复用已验证的执行与可见性包装。"""
import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import cc_worker
from ta_common import PILOT, current
from ta_protocol import validate_pair


if __name__ == '__main__':
    case, reference = current(int(sys.argv[1]))
    validate_pair(reference['case'], case)
    with patch.object(cc_worker, 'PILOT', PILOT):
        cc_worker.execute(case)
