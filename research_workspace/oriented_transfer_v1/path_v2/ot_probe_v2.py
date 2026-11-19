import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import hp_probe
import hp_search
import hp_carry
from register_v2 import RUN
from hv_search import explore
from hv_geometry import inspect

if __name__=='__main__':
    with patch.object(hp_probe,'RUN',RUN),patch.object(hp_search,'explore',explore), \
         patch.object(hp_carry,'inspect',inspect):
        hp_probe.main(*sys.argv[1:])
