"""单策略单条件只执行一次，保留原运行时与观测保护。"""
import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import cc_worker
from cc_runtime import VisibleSession
from rh_runtime import ReturnSession
from fa_common import base, case_at


def main(name, policy):
    folder = base(name, policy)
    session = ReturnSession if policy == 'improved' else VisibleSession
    with patch.object(cc_worker, 'PILOT', folder), patch.object(cc_worker, 'VisibleSession', session):
        cc_worker.execute(case_at(folder))


if __name__ == '__main__':
    main(*sys.argv[1:])
