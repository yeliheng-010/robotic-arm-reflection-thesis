from unittest.mock import patch
import qp_worker
from nd_common import ROOT, verify, change, ACTIONS


if __name__ == '__main__':
    with patch.multiple(qp_worker, ROOT=ROOT, verify=verify, change=change, ACTIONS=ACTIONS):
        qp_worker.main()
