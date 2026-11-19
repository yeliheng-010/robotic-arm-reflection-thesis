"""真实感知与规划后强制停止；禁止执行任何任务轨迹。"""
from unittest.mock import patch
import grasp_process as grasp
import goal_runtime
from cc_runtime import VisibleSession
from routecheck.static import state, unchanged
from cc_common import save


class PlanningComplete(BaseException):
    pass


class UnexpectedMotion(BaseException):
    pass


def reject_motion(*args, **kwargs):
    raise UnexpectedMotion('Planning-only session must never execute task planners')


def stop_after(original, *, folder):
    def choose(flow, **kwargs):
        before = state(flow.robot, flow.env)
        result = original(flow, **kwargs)
        unchanged(before, state(flow.robot, flow.env))
        save(folder/'actual_plan.json', result)
        save(folder/'planning_only.json', dict(stopped_before_task_motion=True,
            planning_state_unchanged=True, physical_attempts=0, model_calls=0))
        raise PlanningComplete()
    return choose


class PlanningSession(VisibleSession):
    def _engine(self):
        with patch.object(goal_runtime, 'choose', stop_after(goal_runtime.choose, folder=self.folder)), \
             patch.object(grasp, '_run_planners', reject_motion):
            super()._engine()
