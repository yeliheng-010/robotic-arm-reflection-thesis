from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import nc_worker
import nc_session
import nc_decide
import sv_client
from top_session import StrategySession
from sv_common import ROOT, verify
from sv_strategy_requests import build
from sv_strategy_actions import check, choose, validate
from sv_strategy_branch import run


if __name__ == '__main__':
    with patch.multiple(nc_worker, ROOT=ROOT, verify=verify, run=run), \
         patch.object(nc_session, 'Session', StrategySession), patch.object(sv_client, 'validate', validate), \
         patch.multiple(nc_decide, build=build, check=check, choose=choose, generate=sv_client.generate):
        nc_worker.main()
