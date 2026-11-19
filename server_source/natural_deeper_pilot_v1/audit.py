from unittest.mock import patch
import qp_audit
from nd_common import ROOT, verify, change, ACTIONS


if __name__ == '__main__':
    with patch.multiple(qp_audit, ROOT=ROOT, verify=verify, change=change, ACTIONS=ACTIONS):
        qp_audit.main()
