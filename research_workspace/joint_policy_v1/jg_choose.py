"""原完整方案优先，失败后在同一观测上扩展抓点与合法关节表示。"""
from unittest.mock import patch
import goal_search
import top_runtime
from cp_candidates import candidates
from jg_geometry import Advisor
from jg_paths import context
from jg_policy import staged


def goals_wrapper(original, advisor):
    def goals(flow, option, endpoints):
        row,targets = original(flow,option,endpoints)
        if not targets:
            return row,targets
        selected = advisor.choose(row)
        return (selected,targets) if selected is not None else (row,[])
    return goals


def choose(flow, *, item, parameters, hooks, events):
    def primary():
        return goal_search.choose(flow,item=item,parameters=parameters,hooks=hooks)
    def fallback():
        advisor = Advisor(flow,item=item,parameters=parameters,record=events.append)
        with patch.object(top_runtime,'candidates',candidates),context(), \
             patch.object(goal_search,'option_goals',goals_wrapper(goal_search.option_goals,advisor)):
            plan = primary()
        if plan['selected'] is None and advisor.budget.used >= advisor.budget.maximum:
            plan['status'] = 'joint_search_budget_exhausted'
        return plan
    return staged(primary,fallback)
