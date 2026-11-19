"""保持选择器、执行器和三次预算，替换场景与可见残差。"""
from unittest.mock import patch
from loopstudy import episode as previous
from expand.bridge import bound
from expand.feedback import project_step


def run(item,directory):
    original=previous.attempt
    def attempt(current,state,*,directory,index):
        return project_step(original(current,state,directory=directory,index=index),current)
    with bound(item),patch.object(previous,'attempt',attempt):
        return previous.run(item,directory)
