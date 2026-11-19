import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import ot_probe
from ot_register_v2 import RUN
from ot_volume_v2 import context

if __name__=='__main__':
    with context(),patch.object(ot_probe,'RUN',RUN):
        ot_probe.main(*sys.argv[1:])
