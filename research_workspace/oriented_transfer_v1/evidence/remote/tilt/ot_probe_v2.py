import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import ot_probe
from register import RUN
from ot_volume_v2 import context
from tt_endpoints import inspect

if __name__=='__main__':
    with context(),patch.object(ot_probe,'RUN',RUN),patch.object(ot_probe,'inspect',inspect):
        ot_probe.main(*sys.argv[1:])
