from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import nc_worker
import nc_session
import nc_decide
from span_runtime import SpanSession
from sv_common import ROOT, verify
from sv_requests_v2 import build
from sv_actions import check, choose
from sv_client import generate


if __name__ == '__main__':
    with patch.multiple(nc_worker, ROOT=ROOT, verify=verify), patch.object(nc_session, 'Session', SpanSession), \
         patch.multiple(nc_decide, build=build, check=check, choose=choose, generate=generate):
        nc_worker.main()
