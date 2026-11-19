"""真实入口零运动检查后，独立进程只执行一次完整任务。"""
import sys
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import nc_session
import cc_worker
from jp_common import TRIAL, SOURCE, registered, prepare, read, save, sha, verify
from jp_runtime import JointSession, PlanningSession, PlanningComplete


def pair(folder):
    paths = [SOURCE/'span_inputs.npz',folder/'span_inputs.npz']
    with np.load(paths[0]) as old,np.load(paths[1]) as current:
        assert set(old.files) == set(current.files)
        for name in old.files:
            np.testing.assert_array_equal(old[name],current[name])
        fields = old.files
    return dict(passed=True,identical_arrays=fields,identities={str(p):sha(p) for p in paths})


def preflight():
    case = registered()
    folder = TRIAL/'preflight'
    caught = False
    try:
        with patch.object(nc_session,'Session',PlanningSession):
            with nc_session.opened(case,case['state'],folder=folder,index=1):
                raise AssertionError('Planning-only unexpectedly returned')
    except PlanningComplete:
        caught = True
    assert caught and read(folder/'approved_plan_match.json')['stopped_before_motion']
    assert read(folder/'bridge.json')['planners'] == []
    assert not (folder/'step.json').exists()
    assert read(folder/'initial_visibility.json')['accepted']
    lifecycle = read(folder/'lifecycle.json')
    assert lifecycle['released'] and lifecycle['actual_close_calls'] == 1
    assert lifecycle['exit_exception'] == 'PlanningComplete'
    save(TRIAL/'preflight_result.json',dict(passed=True,physical_attempts=0,inputs=pair(folder)))


def execute():
    assert read(TRIAL/'preflight_result.json')['passed']
    with patch.object(cc_worker,'PILOT',TRIAL),patch.object(cc_worker,'VisibleSession',JointSession):
        cc_worker.execute(registered())


if __name__ == '__main__':
    {'prepare':prepare,'preflight':preflight,'execute':execute}[sys.argv[1]]()
