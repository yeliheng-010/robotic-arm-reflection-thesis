import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import nc_session
from qa_runtime import PlanningComplete
from surface_physical_v1.gate import claim
from surface_physical_v1.replay import pair
from held_observation_v1.common import TRIAL,read,save,registered
from held_observation_v1.register import prepare,execution
from held_observation_v1.runtime import Session,PreviewSession
from held_observation_v1.pause import CaptureComplete


def preflight():
    case=registered()['case']
    folder=TRIAL/'preflight'
    stopped=False
    try:
        with patch.object(nc_session,'Session',PreviewSession):
            with nc_session.opened(case,case['state'],folder=folder,index=1):
                raise AssertionError('Unexpected task motion')
    except PlanningComplete:
        stopped=True
    assert stopped and read(folder/'bridge.json')['planners']==[]
    assert read(folder/'strict_held_precheck.json')['passed']
    assert read(folder/'lifecycle.json')['actual_close_calls']==1
    observation=read(folder/'checkpoints/preflight/result.json')
    save(TRIAL/'preflight_result.json',dict(passed=observation['quality_passed'],
        physical_attempts=0,inputs=pair(folder),observation=observation))
    print(dict(preflight_passed=observation['quality_passed'],physical_attempts=0),flush=True)


def execute():
    claim(TRIAL)
    case=registered()['case']
    folder=TRIAL/'cases/964347/first'
    result=dict(physical_attempts=1,release_executed=False,task_success=None,
        model_calls=0,training_eligible=False,stopped_before_release=False)
    try:
        with patch.object(nc_session,'Session',Session):
            with nc_session.opened(case,case['state'],folder=folder,index=1):
                raise AssertionError('Unexpected release continuation')
    except CaptureComplete:
        result['stopped_before_release']=True
    except BaseException as error:
        result.update(exception=type(error).__name__,message=str(error))
        raise
    finally:
        save(TRIAL/'outcome.json',result)
    assert not read(folder/'guard.json')['open_called']
    assert read(folder/'lifecycle.json')['actual_close_calls']==1
    print(result,flush=True)


if __name__=='__main__':
    {'prepare':prepare,'preflight':preflight,'register':execution,'execute':execute}[sys.argv[1]]()
