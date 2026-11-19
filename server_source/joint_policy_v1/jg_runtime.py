"""通用入口从本次规划读取关节候选，不绑定种子、目标或旧路径。"""
from unittest.mock import patch
import grasp_process as grasp
import goal_runtime
import rb_runtime
from rh_runtime import ReturnSession
from jp_runtime import replace
from cc_common import save
from jg_choose import choose


def prefix_factory(original_factory):
    def factory(original, trace):
        wrapped = original_factory(original,trace)
        def move(*args,**kwargs):
            option = trace['selected'].get('joint_option')
            if option is None:
                return wrapped(*args,**kwargs)
            backend,count = grasp._run_planners,[0]
            def run(*values,**named):
                assert not named
                selected = dict(path=option['waypoints'],option=option)
                changed = replace(values,selected) if count[0] == 0 else values
                count[0] += 1
                return backend(*changed)
            with patch.object(grasp,'_run_planners',run):
                result = wrapped(*args,**kwargs)
            assert count[0] == 3
            return result
        return move
    return factory


class GeneralSession(ReturnSession):
    def _engine(self):
        events = []
        def selecting(flow,**kwargs):
            plan = choose(flow,events=events,**kwargs)
            save(self.folder/'generic_plan.json',plan)
            return plan
        try:
            with patch.object(goal_runtime,'choose',selecting), \
                 patch.object(rb_runtime,'prefix_wrapper',prefix_factory(rb_runtime.prefix_wrapper)):
                super()._engine()
        finally:
            save(self.folder/'joint_candidates.json',events)
