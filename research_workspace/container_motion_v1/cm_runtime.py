"""只在第三次反馈触发的新执行器，公共源码和旧实验保持不变。"""
from contextlib import contextmanager
from unittest.mock import patch
import numpy as np
import spatialmath as sm
import grasp_process as grasp
import stability.prepose as prepose
from loopstudy import runtime as base_runtime, episode
from cm_pose import eligible
from cm_planning import choose

BASE_ENGINE = base_runtime.engine_class


def selector(hooks, trace, *, item, parameters):
    def apply(flow, *, ignore):
        assert tuple(ignore)==(item['source'],item['destination'])
        plan = choose(flow,hooks,parameters=parameters,item=item)
        trace.update(plan)
        if plan['selected'] is None:
            trace['fallback'] = 'original_rule_pose_no_static_feasible_candidate'
            return hooks[2](flow,ignore=ignore)
        row = plan['candidates'][plan['selected']]
        flow.T_wo = sm.SE3(np.array(row['pose']))
        flow.q1 = np.array(row['q1'])
        trace['fallback'] = None
        return row['prepose']
    return apply


def engine_class(state, *, policy, item, feedback):
    active = policy=='geometry' and eligible(feedback)
    parent = BASE_ENGINE(state)
    class MotionEngine(parent):
        def _attempt(self, *args, **kwargs):
            trace = dict(policy=policy,active=active,feedback=feedback,training_approved=False)
            hooks = (grasp.move_to_grasp_pose,grasp.move_to_point,prepose.select_prepose)
            with capture(active,hooks,trace,item=item,parameters=state['parameters']):
                record,report = super()._attempt(*args,**kwargs)
            record['motion_extension'] = trace
            return record,report
    return MotionEngine


@contextmanager
def capture(active, hooks, trace, *, item, parameters):
    if active:
        with patch.object(prepose,'select_prepose',selector(hooks,trace,item=item,parameters=parameters)):
            yield
    else:
        yield


def attempt(item, state, *, directory, policy, feedback):
    factory = lambda current: engine_class(current,policy=policy,item=item,feedback=feedback)
    with patch.object(base_runtime,'engine_class',factory):
        return episode.attempt(item,state,directory=directory,index=3)
