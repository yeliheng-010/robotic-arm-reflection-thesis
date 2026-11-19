"""保留原方案优先，为扩展候选使用独立的同观测审计账本。"""
from unittest.mock import patch
import goal_search
from top_runtime import candidates as original_candidates
from cp_candidates import candidates as expanded_candidates
from jg_geometry import Advisor
from jg_paths import context
from jg_choose import goals_wrapper
from jg_policy import staged
from jv_context import stage


def choose(flow, *, item, parameters, hooks, events):
    def plan():
        return goal_search.choose(flow,item=item,parameters=parameters,hooks=hooks)
    def primary():
        return stage(original_candidates,plan)
    def fallback():
        advisor = Advisor(flow,item=item,parameters=parameters,record=events.append)
        with context(),patch.object(goal_search,'option_goals',goals_wrapper(goal_search.option_goals,advisor)):
            result = stage(expanded_candidates,plan)
        if result['selected'] is None and advisor.budget.used >= advisor.budget.maximum:
            result['status'] = 'joint_search_budget_exhausted'
        return result
    return staged(primary,fallback)
