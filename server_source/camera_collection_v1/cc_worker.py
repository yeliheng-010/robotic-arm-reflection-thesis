"""每个固定布局只执行一次；私有审计留图不等于公开模型输入。"""
import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import nc_session
from nc_session import opened
from live_observations import Sampler
from cc_runtime import VisibleSession, GuardedSampler
from cc_policy import VisibilityRejected
from cc_common import PILOT, current, read, save, sha


def summary(sampler):
    return dict(public=sampler.rows, private=sampler.private,
        paths=[str(sampler.folder/'observation_0')], remaining=sampler.budget.remaining)


def observation(session, folder):
    arguments = dict(item=session.case['item'], attempt=1, success=session.step['success'])
    sampler = GuardedSampler(session.lease.env, session.case['config'],
        folder=folder/'observations', **arguments)
    try:
        sampler.capture()
        allowed = True
    except VisibilityRejected:
        allowed = False
        sampler = Sampler(session.lease.env, session.case['config'],
            folder=folder/'private_audit', **arguments)
        sampler.capture()
    save(folder/'observation_summary.json', summary(sampler))
    save(folder/'publication.json', dict(public_input_allowed=allowed,
        purpose='model_input_eligible' if allowed else 'private_physical_audit_only',
        model_calls=0, training_eligible=False))
    return allowed


def execute(case):
    seed = case['item']['seed']
    qualification = read(PILOT/'qualification'/str(seed)/'result.json')
    assert qualification['qualified'] is True
    assert qualification['manifest_sha256'] == sha(PILOT/'manifest.json')
    case = dict(case, qualification=qualification['geometry'])
    folder = PILOT/'cases'/str(seed)
    folder.mkdir(parents=True, exist_ok=False)
    with patch.object(nc_session, 'Session', VisibleSession):
        with opened(case, case['state'], folder=folder/'first', index=1) as session:
            allowed = observation(session, folder/'first')
            success = session.step['success']
    save(folder/'result.json', dict(seed=seed, physical_attempts=1, model_calls=0,
        new_success=success, public_input_allowed=allowed, training_eligible=False,
        manifest_sha256=sha(PILOT/'manifest.json')))
    print(dict(seed=seed, new_success=success, public_input_allowed=allowed), flush=True)


if __name__ == '__main__':
    execute(current(int(sys.argv[1])))
