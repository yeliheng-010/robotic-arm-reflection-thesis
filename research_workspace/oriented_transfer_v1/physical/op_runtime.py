from unittest.mock import patch
import grasp_process as grasp
import goal_runtime
import rb_runtime
import top_runtime
from lc_candidates import candidates
from rh_runtime import ReturnSession
from jg_runtime import prefix_factory
from qa_runtime import reject_motion
from op_choose import selecting
from op_carry import factory


class Session(ReturnSession):
    planning_only=False

    def _engine(self):
        def carry(original,trace):
            return factory(original,trace,session=self)
        with patch.object(top_runtime,'candidates',candidates), \
             patch.object(goal_runtime,'choose',selecting(self)), \
             patch.object(rb_runtime,'prefix_wrapper',prefix_factory(rb_runtime.prefix_wrapper)), \
             patch.object(rb_runtime,'carry_wrapper',carry):
            super()._engine()


class PreviewSession(Session):
    planning_only=True

    def _engine(self):
        with patch.object(grasp,'_run_planners',reject_motion):
            super()._engine()
