"""仅在独立worker进程内改变预算或反馈缺失，保持原item和物理配置。"""
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
from hardstudy.feedback import project_step
from hardstudy import episode as hard_episode, audit as hard_audit
from loopstudy import episode, audit

BUDGETS={'budget4':4,'no_missing':3}


def project_variant(step,item,*,variant):
    assert variant in BUDGETS
    effective=item
    if variant=='no_missing':
        effective=dict(item,noise_profile=dict(item['noise_profile'],missing_probability=0.))
    return project_step(step,effective)


@contextmanager
def configured(entry):
    name=entry['variant']
    assert name in BUDGETS and entry['max_attempts']==BUDGETS[name]
    def project(step,item):
        return project_variant(step,item,variant=name)
    with ExitStack() as stack:
        stack.enter_context(patch.object(episode,'MAX_ATTEMPTS',BUDGETS[name]))
        stack.enter_context(patch.object(audit,'MAX_ATTEMPTS',BUDGETS[name]))
        stack.enter_context(patch.object(hard_episode,'project_step',project))
        stack.enter_context(patch.object(hard_audit,'project_step',project))
        yield
