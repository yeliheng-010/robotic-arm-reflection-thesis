from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import ot_run_v2
from register_v2 import ROOT,RUN

if __name__=='__main__':
    with patch.object(ot_run_v2,'ROOT',ROOT),patch.object(ot_run_v2,'RUN',RUN):
        ot_run_v2.main()
