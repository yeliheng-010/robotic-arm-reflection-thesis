from unittest.mock import patch
import numpy as np
import spatialmath as sm
import grasp_process as grasp
from reflection.monitors import abort,ErrorType
from routecheck.clone import clone_robot
from rh_runtime import robot_context
from live_motion import plan_values
from hv_geometry import inspect
from surface_physical_v1.common import save
from surface_physical_v1.scope import COLLECTING


def check_and_run(backend,values,*,trace,folder):
    robot,env,planners,durations=values[:4]
    assert len(planners)==3 and len(durations)==4 and durations[0]==0.
    segments=list(zip(('lift','transport','descent'),planners,durations[1:]))
    pose=sm.SE3(np.asarray(trace['selected']['pose']))
    checked=inspect(clone_robot(robot),env,segments,item=trace['_surface_item'],grasp=pose)
    save(folder/'live_held_check.json',dict(context=robot_context(robot,env),grasp=pose.A.tolist(),
        legs=plan_values(segments),result=checked))
    if not checked['feasible']:
        abort(ErrorType.COLLISION,'Current held-object path rejected',
              route_planning_rejected=True,guard_kind='live_held_object_path')
    return backend(*values)


def factory(original_factory,*,folder):
    def wrap(original,trace):
        wrapped=original_factory(original,trace)
        def move(*args,**kwargs):
            if COLLECTING.get():
                return wrapped(*args,**kwargs)
            backend=grasp._run_planners
            def checked(*values,**named):
                assert not named
                return check_and_run(backend,values,trace=trace,folder=folder)
            with patch.object(grasp,'_run_planners',checked):
                return wrapped(*args,**kwargs)
        return move
    return wrap
