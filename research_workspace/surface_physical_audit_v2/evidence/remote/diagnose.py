from pathlib import Path
from contextlib import nullcontext
from unittest.mock import patch
import numpy as np
import mujoco
from reflection.__main__ import bootstrap
bootstrap()
import top_runtime
import goal_search
from audit_motion_live import UR5e,set_robot_config,guard_context
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from rv_runtime import mode
from route_audit_v3 import rebuild
from model_grasp_gpu_v1.planning import search,integration,forbid,deadline
from surface_physical_v1.common import TRIAL,PROJECT,read,save,entry,frozen_plan
from surface_physical_v1.replay import candidate

ROOT=Path(__file__).resolve().parent


def measure(fixed):
    case=entry()['case']
    trace=read(TRIAL/'cases/964347/first/route.json')
    points=np.asarray(read(PROJECT/'model_grasp_gpu_v1/observation.json')['target_points'])
    configure=patch.object(UR5e,'set_robot_config',set_robot_config) if fixed else nullcontext()
    guarding=guard_context(case['item'],{}) if fixed else nullcontext()
    with configure,guarding,self_context(),joint_context(case['config']),mode(case['control']), \
         patch.object(top_runtime,'candidates',candidate()),top_runtime.filter_context(points,{}), \
         patch.object(goal_search,'LIFTS',(.2,)),patch.object(mujoco,'mj_step',forbid), \
         patch.object(mujoco,'mj_step1',forbid),patch.object(mujoco,'mj_step2',forbid),deadline(180):
        flow=rebuild(case,trace)
        before=integration(flow)
        plan=search(flow,case,[])
        np.testing.assert_array_equal(before,integration(flow))
    expected=frozen_plan()
    differences=[key for key in expected if plan[key]!=expected[key]]
    save(ROOT/('guarded_plan.json' if fixed else 'unpatched_plan.json'),plan)
    return dict(matches=not differences,different_fields=differences,
        endpoint_passing=plan['endpoints']['passing'],selected=plan['selected'] is not None,
        state_unchanged=True,physical_attempts=0)


if __name__=='__main__':
    result=dict(unpatched=measure(False),guarded=measure(True))
    save(ROOT/'diagnostic.json',result)
    print(result,flush=True)
