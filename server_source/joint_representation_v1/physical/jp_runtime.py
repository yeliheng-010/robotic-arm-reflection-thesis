"""真实入口先核对冻结完整计划，再只替换首个预抓取关节段。"""
from unittest.mock import patch
import numpy as np
import grasp_process as grasp
import goal_runtime
import rb_runtime
import top_runtime
from cp_candidates import candidates
from rh_runtime import ReturnSession
from rh_planner import planners
from qa_runtime import PlanningComplete, reject_motion
from jr_scope import context
from jp_common import PARENT, RUN, read, save, sha


class PlanMismatch(BaseException):
    pass


def replace(values, selection):
    assert len(values) == 6 and len(values[2]) == 1
    original = values[2][0]
    duration = values[3][1]
    np.testing.assert_array_equal(original.interpolate(0.),selection['path'][0])
    np.testing.assert_allclose(original.interpolate(duration),selection['path'][-1],atol=1e-12,rtol=0)
    changed = list(values)
    changed[2] = planners(selection['option'])
    changed[3] = [0.,*selection['option']['durations']]
    return changed


def prefix_factory(original_factory, selection):
    def factory(original, trace):
        wrapped = original_factory(original,trace)
        def move(*args, **kwargs):
            backend, count = grasp._run_planners, [0]
            def run(*values, **named):
                assert not named
                changed = replace(values,selection) if count[0] == 0 else values
                count[0] += 1
                return backend(*changed)
            with patch.object(grasp,'_run_planners',run):
                result = wrapped(*args,**kwargs)
            assert count[0] == 3
            return result
        return move
    return factory


def checked_choose(original, session):
    def choose(flow, **kwargs):
        plan = original(flow,**kwargs)
        expected = read(PARENT/'full/plan.json')
        if plan != expected:
            save(session.folder/'mismatched_plan.json',plan)
            raise PlanMismatch('Actual observation/planning differs from certified snapshot')
        save(session.folder/'approved_plan_match.json',dict(passed=True,
            actual_plan_identical=True,expected_sha256=sha(PARENT/'full/plan.json'),
            stopped_before_motion=session.planning_only))
        if session.planning_only:
            raise PlanningComplete()
        return plan
    return choose


class JointSession(ReturnSession):
    planning_only = False

    def _engine(self):
        selected = read(RUN/'result.json')['selected']
        factory = prefix_factory(rb_runtime.prefix_wrapper,selected)
        with patch.object(top_runtime,'candidates',candidates),context(selected), \
             patch.object(rb_runtime,'prefix_wrapper',factory), \
             patch.object(goal_runtime,'choose',checked_choose(goal_runtime.choose,self)):
            super()._engine()


class PlanningSession(JointSession):
    planning_only = True

    def _engine(self):
        with patch.object(grasp,'_run_planners',reject_motion):
            super()._engine()
