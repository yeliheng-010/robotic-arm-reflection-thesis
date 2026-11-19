from unittest.mock import patch
import grasp_process as grasp
import top_runtime
import goal_runtime
import rb_runtime
import loopstudy.runtime as loop
from rh_runtime import ReturnSession
from jg_runtime import prefix_factory
from qa_runtime import reject_motion
from surface_physical_v1.replay import candidate,selecting
from surface_physical_v1.held import factory
from surface_physical_v1.scope import collection


class Session(ReturnSession):
    planning_only=False

    def _engine(self):
        choose=selecting(self)
        def select(flow,**kwargs):
            result=choose(flow,**kwargs)
            result['_surface_item']=self.case['item']
            return result
        with patch.object(top_runtime,'candidates',candidate()), \
             patch.object(goal_runtime,'choose',select), \
             patch.object(rb_runtime,'prefix_wrapper',prefix_factory(rb_runtime.prefix_wrapper)), \
             patch.object(rb_runtime,'carry_wrapper',factory(rb_runtime.carry_wrapper,folder=self.folder)), \
             patch.object(loop,'plans',collection(loop.plans)):
            super()._engine()


class PreviewSession(Session):
    planning_only=True

    def _engine(self):
        with patch.object(grasp,'_run_planners',reject_motion):
            super()._engine()
