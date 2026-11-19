"""新数据采集入口，与历史 collect_worker 隔离。"""
import os
import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import nc_session
import sv_requests_v2
from top_session import StrategySession
from nc_session import opened
from nc_observation import View
from rc_branch import run
from collection_common import BRANCHES, PHYSICS, save, sha, verify


def execute(case):
    folder = PHYSICS/'cases'/case['item']['id']
    folder.mkdir(parents=True, exist_ok=False)
    rows = {}
    with opened(case, case['state'], folder=folder/'first', index=1) as first:
        shared = View(first, folder=folder/'first/observations', remaining=2)
        save(folder/'first/observation_summary.json', shared.summary())
        for method in BRANCHES:
            result = run(case, first, shared=shared, method=method, folder=folder/method)
            rows[method] = {k:result[k] for k in ('success','new_attempts','model_calls','extra_observations')}
            print(case['item']['id'], method, rows[method], flush=True)
    count = 1+sum(r['new_attempts'] for r in rows.values())
    assert count <= 7
    save(folder/'result.json', dict(methods=rows, attempts=count, model_calls=0,
        manifest_sha256=sha(PHYSICS/'manifest.json'), status='completed'))


if __name__ == '__main__':
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify(PHYSICS/'manifest.json')
    case = next(c for c in manifest['cases'] if c['item']['id'] == sys.argv[1])
    with patch.object(nc_session, 'Session', StrategySession), patch.object(sv_requests_v2, 'ROOT', PHYSICS):
        execute(case)
    verify(PHYSICS/'manifest.json')
