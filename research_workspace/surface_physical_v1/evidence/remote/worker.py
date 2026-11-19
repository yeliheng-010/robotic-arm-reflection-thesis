import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import nc_session
import cc_worker
from qa_runtime import PlanningComplete
from surface_physical_v1.common import TRIAL,read,save,entry
from surface_physical_v1.register import prepare,execution
from surface_physical_v1.gate import claim
from surface_physical_v1.runtime import Session,PreviewSession
from surface_physical_v1.replay import pair


def preflight():
    case=entry()['case']
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
    assert lifecycle['close_error'] is None and lifecycle['exit_exception']=='PlanningComplete'
    held=read(folder/'strict_held_precheck.json')
    result=dict(passed=held['passed'],physical_attempts=0,inputs=pair(folder),strict_held=held)
    save(TRIAL/'preflight_result.json',result)
    print(dict(preflight_passed=result['passed'],physical_attempts=0),flush=True)


def execute():
    claim(TRIAL)
    outcome=dict(returned=False,exception=None,model_calls=0,training_updates=0)
    try:
        with patch.object(cc_worker,'PILOT',TRIAL),patch.object(cc_worker,'VisibleSession',Session):
            cc_worker.execute(entry()['case'])
        outcome['returned']=True
    except BaseException as error:
        outcome.update(exception=type(error).__name__,message=str(error))
        raise
    finally:
        save(TRIAL/'execution_outcome.json',outcome)


if __name__=='__main__':
    {'prepare':prepare,'preflight':preflight,'register':execution,'execute':execute}[sys.argv[1]]()
