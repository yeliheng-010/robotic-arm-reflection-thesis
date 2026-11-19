"""保留原独立物理审计并核对实际预抓取命令与冻结候选一致。"""
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import top_runtime
from cp_candidates import candidates
from rh_audit import inspect
from live_motion import plan_values
from rh_planner import planners
from jr_scope import context
from jp_common import TRIAL, RUN, registered, read, save, sha, verify
from jp_worker import pair


def commands(folder, selected):
    bridge = read(folder/'bridge.json')
    executed = bridge['planners'][0]
    assert executed['executed']
    option = selected['option']
    segments = [(executed['action']+'_'+str(i),p,t)
                for i,(p,t) in enumerate(zip(planners(option),option['durations']))]
    assert executed['legs'] == plan_values(segments)
    assert executed['durations'] == [0.,*option['durations']]
    np.testing.assert_array_equal(executed['context']['robot_q'],selected['path'][0])
    return dict(passed=True,duration=sum(option['durations']),legs=len(segments))


def main():
    case = registered()
    folder = TRIAL/'cases'/str(case['item']['seed'])/'first'
    selected = verify(RUN/'result.json')['selected']
    assert read(folder/'approved_plan_match.json')['actual_plan_identical']
    command = commands(folder,selected)
    inputs = pair(folder)
    with patch.object(top_runtime,'candidates',candidates),context(selected):
        result = inspect(case,base=TRIAL)
    verify(TRIAL/'manifest.json')
    paths = [p for p in (TRIAL/'cases').rglob('*') if p.is_file()]
    result.update(command=command,inputs=inputs,physical_attempts=1,model_calls=0,
        identities={str(p):sha(p) for p in paths})
    save(TRIAL/'audit.json',result)
    assert result['passed'], result
    print(dict(passed=True,success=result['success'],physical_attempts=1),flush=True)


if __name__ == '__main__':
    main()
