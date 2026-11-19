import numpy as np
import spatialmath as sm
from unittest.mock import patch
from action_space_audit_v1.scene import opened
import goal_search
from jv_context import observation,stage
from model_grasp_gpu_v1.planning import search,deadline
from model_grasp_intent_v1.geometry import MAX_TRANSLATION_M,MAX_WIDTH_M,WIDTH_MARGIN_M
from natural_grasp_span_audit_v1.span import span
from surface_grasp_v1.common import ROOT,PROJECT,read,save


def generator(row, points, called):
    pose=sm.SE3(np.asarray(row['proposal']['pose']))
    def provide(nominal, fitted):
        assert fitted['available']
        assert np.linalg.norm(pose.t-nominal.t)<=MAX_TRANSLATION_M
        assert span(points,pose.R[:,1])+WIDTH_MARGIN_M<=MAX_WIDTH_M
        called.append(True)
        return [dict(id=row['id'],pose=pose)]
    return provide


def inspect(row, manifest, folder):
    points=np.asarray(read(PROJECT/'model_grasp_gpu_v1/observation.json')['target_points'])
    trace,events,called={ },[],[]
    lift=manifest['case']['state']['parameters']['lift_height']
    with opened(manifest) as flow,observation(points,trace),patch.object(goal_search,'LIFTS',(lift,)):
        with deadline(manifest['planning_timeout_s']):
            plan=stage(generator(row,points,called),lambda: search(flow,manifest['case'],events))
        assert called and trace['poses']
        save(folder/'private_plan.json',plan)
        save(folder/'private_trace.json',trace)
        save(folder/'private_events.json',events)
    save(folder/'state_check.json',dict(unchanged=True,integration_identical=True,physical_attempts=0))
    return dict(status='ready' if plan['selected'] is not None else 'rejected')
