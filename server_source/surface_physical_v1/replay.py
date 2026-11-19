from unittest.mock import patch
import mujoco
import numpy as np
import spatialmath as sm
import grasp_process as grasp
import goal_search
from routecheck.clone import clone_robot
from routecheck.static import state,unchanged
from route_geometry import inspect as robot_check
from waypoint_paths import collect
from waypoint_search import proxy
from jg_paths import context as paths_context
from hv_geometry import inspect as held_check
from model_grasp_gpu_v1.planning import search,integration,forbid,deadline
from surface_grasp_v1.planning import generator
from surface_physical_v1.common import STATIC,SOURCE,PROJECT,read,save,sha,entry,selected,frozen_plan


def candidate():
    points=read(PROJECT/'model_grasp_gpu_v1/observation.json')['target_points']
    return generator(selected(),np.asarray(points),[])


def pair(folder):
    with np.load(SOURCE/'span_inputs.npz') as old,np.load(folder/'span_inputs.npz') as new:
        assert set(old.files)==set(new.files)
        for name in old.files:
            np.testing.assert_array_equal(old[name],new[name])
        names=list(old.files)
    return dict(passed=True,identical_arrays=names,source_sha256=sha(SOURCE/'span_inputs.npz'))


def strict_path(flow,plan,*,case,hooks):
    row=plan['selected']
    parameters=case['state']['parameters']
    edges=np.asarray(plan['edges'])
    checker=clone_robot(flow.robot)
    with paths_context():
        prefix=collect(proxy(flow,row),hooks[0],parameters=parameters,
            phase='prefix',route=row['approach_route'],edges=edges)
        first=robot_check(checker,flow.env,prefix,item=case['item'])
        assert first['feasible']
        carry=collect(proxy(flow,row),hooks[1],parameters=parameters,phase='carry',
            route=row['transport_route'],edges=edges,target=row['target'])
    held=held_check(checker,flow.env,carry,item=case['item'],grasp=sm.SE3(np.asarray(row['pose'])))
    return dict(passed=held['feasible'],prefix=first,held=held,physical_attempts=0)


def replay(flow,case,*,hooks):
    before,full=state(flow.robot,flow.env),integration(flow)
    events=[]
    with patch.object(grasp,'move_to_grasp_pose',hooks[0]),patch.object(grasp,'move_to_point',hooks[1]), \
         patch.object(goal_search,'LIFTS',(case['state']['parameters']['lift_height'],)), \
         patch.object(mujoco,'mj_step',forbid),patch.object(mujoco,'mj_step1',forbid), \
         patch.object(mujoco,'mj_step2',forbid),deadline(180):
        try:
            plan=search(flow,case,events)
            assert plan==frozen_plan(),'Real entry differs from frozen static plan'
            assert events==read(STATIC/'paths/audit'/selected()['id']/'private_events.json')
            strict=strict_path(flow,plan,case=case,hooks=hooks)
        finally:
            unchanged(before,state(flow.robot,flow.env))
            np.testing.assert_array_equal(full,integration(flow))
    return plan,strict


def selecting(session):
    def choose(flow,**kwargs):
        row=entry()
        for key in ('item','config','state','control','strategy'):
            assert session.case[key]==row['case'][key]
        assert kwargs['item']==row['case']['item'] and kwargs['parameters']==row['case']['state']['parameters']
        inputs=pair(session.folder)
        plan,strict=replay(flow,row['case'],hooks=kwargs['hooks'])
        save(session.folder/'actual_plan.json',plan)
        save(session.folder/'strict_held_precheck.json',strict)
        save(session.folder/'approved_plan_match.json',dict(passed=True,inputs=inputs,
            actual_plan_identical=True,integration_identical=True,stopped_before_motion=session.planning_only))
        if session.planning_only:
            from qa_runtime import PlanningComplete
            raise PlanningComplete()
        assert strict['passed'],'Strict held-path precheck failed'
        return plan
    return choose
