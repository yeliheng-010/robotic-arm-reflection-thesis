from unittest.mock import patch
import qp_worker
from span_runtime import SpanSession
from sp_common import ROOT, verify, change, ACTIONS


if __name__ == '__main__':
    with patch.multiple(qp_worker, ROOT=ROOT, verify=verify, change=change, ACTIONS=ACTIONS, QualifiedSession=SpanSession):
        qp_worker.main()
