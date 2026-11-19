import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import nc_session
import cc_worker
from qa_runtime import PlanningComplete
from op_common import TRIAL,entry,prepare,read,save
from op_runtime import Session,PreviewSession
from op_choose import pair


def preflight():
    row=entry()
    case=row['case']
    folder=TRIAL/'preflight'
    caught=False
    try:
        with patch.object(nc_session,'Session',PreviewSession):
            with nc_session.opened(case,case['state'],folder=folder,index=1):
                raise AssertionError('Unexpected motion entry')
    except PlanningComplete:
        caught=True
    assert caught and read(folder/'approved_plan_match.json')['stopped_before_motion']
    assert read(folder/'bridge.json')['planners']==[] and not (folder/'step.json').exists()
    assert read(folder/'initial_visibility.json')['accepted']
    lifecycle=read(folder/'lifecycle.json')
    assert lifecycle['released'] and lifecycle['actual_close_calls']==1
    assert lifecycle['exit_exception']=='PlanningComplete'
    save(TRIAL/'preflight_result.json',dict(passed=True,physical_attempts=0,inputs=pair(folder)))
    print(dict(preflight_passed=True,physical_attempts=0),flush=True)


def execute():
    assert read(TRIAL/'preflight_result.json')['passed']
    with patch.object(cc_worker,'PILOT',TRIAL),patch.object(cc_worker,'VisibleSession',Session):
        cc_worker.execute(entry()['case'])


if __name__=='__main__':
    {'prepare':prepare,'preflight':preflight,'execute':execute}[sys.argv[1]]()
