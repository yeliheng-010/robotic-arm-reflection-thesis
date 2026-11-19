import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import jg_probe
from jv_register import RUN
from jv_context import observation
from jv_choose import choose


if __name__ == '__main__':
    with patch.object(jg_probe,'RUN',RUN),patch.object(jg_probe,'filter_context',observation), \
         patch.object(jg_probe,'choose',choose):
        jg_probe.main(*sys.argv[1:])
