import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import jg_probe
import jv_choose
from jv_context import observation
from yc_candidates import candidates
from yc_register import RUN


if __name__ == '__main__':
    with patch.object(jg_probe,'RUN',RUN),patch.object(jg_probe,'filter_context',observation), \
         patch.object(jg_probe,'choose',jv_choose.choose),patch.object(jv_choose,'expanded_candidates',candidates):
        jg_probe.main(*sys.argv[1:])
