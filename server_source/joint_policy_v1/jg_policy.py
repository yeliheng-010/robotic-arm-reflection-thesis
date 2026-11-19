"""安全原方案优先及全局检查预算。"""
from itertools import chain


class Budget:
    def __init__(self, maximum):
        if type(maximum) is not int or maximum < 1:
            raise ValueError('Positive integer budget required')
        self.maximum,self.used = maximum,0


def select(original, alternatives, *, check, budget, record):
    for option in chain((original,),alternatives):
        if budget.used >= budget.maximum:
            return None
        budget.used += 1
        passed = check(option)
        if type(passed) is not bool:
            raise TypeError('Boolean safety decision required')
        record(dict(option=option,accepted=passed,index=budget.used))
        if passed:
            return option
    return None


def staged(primary, fallback):
    plan = primary()
    return plan if plan['selected'] is not None else fallback()
