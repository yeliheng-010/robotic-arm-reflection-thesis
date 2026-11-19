"""固定首次传感噪声，只获得真实入口的规划证据。"""
import sys
from copy import deepcopy
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import nc_session
from qa_runtime import PlanningSession, PlanningComplete
from qs_common import ROOT, current, read, save, sha, verify

RUN = ROOT/'actual'


def main(name):
    verify(RUN/'manifest.json')
    case = deepcopy(current(name)['case'])
    case['strategy'] = 'observed_top'
    folder = RUN/'cases'/name
    caught = False
    try:
        with patch.object(nc_session, 'Session', PlanningSession):
            with nc_session.opened(case, case['state'], folder=folder, index=1):
                raise AssertionError('Planning-only session must stop before yielding an execution')
    except PlanningComplete:
        caught = True
    assert caught and read(folder/'planning_only.json')['stopped_before_task_motion']
    assert not read(folder/'bridge.json')['planners']
    assert not (folder/'step.json').exists()
    lifecycle = read(folder/'lifecycle.json')
    assert lifecycle['released'] and lifecycle['actual_close_calls'] == 1
    assert lifecycle['exit_exception'] == 'PlanningComplete'
    paths = [p for p in folder.rglob('*') if p.is_file()]
    plan, span = read(folder/'actual_plan.json'), read(folder/'span_guard.json')
    save(folder/'result.json', dict(case=case, passed=True, qualified=plan['selected'] is not None,
        status=plan['status'], nominal=plan['context']['nominal'], span=span,
        stopped_before_task_motion=True, physical_attempts=0, model_calls=0,
        identities={str(p): sha(p) for p in paths}))
    print(dict(id=name, qualified=plan['selected'] is not None), flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
