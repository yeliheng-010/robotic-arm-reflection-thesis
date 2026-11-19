"""保留原选择流程，仅在物理尝试中持续施加预登记干预。"""
from unittest.mock import patch
from loopstudy import episode as previous
from hardstudy.bridge import bound
from hardstudy.feedback import project_step
from hardstudy.intervention import attempt as physical_attempt


def run(item,directory):
    def attempt(current,state,*,directory,index):
        step=physical_attempt(current,state,directory=directory,index=index)
        return project_step(step,current)
    with bound(item),patch.object(previous,'attempt',attempt):
        return previous.run(item,directory)
