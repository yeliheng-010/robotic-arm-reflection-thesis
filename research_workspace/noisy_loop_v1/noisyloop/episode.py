"""原闭环执行后只替换可见反馈，不改变物理评价。"""
from unittest.mock import patch
from loopstudy import episode as previous
from noisyloop.feedback import project_step


def run(item,directory):
    original=previous.attempt
    def attempt(current,state,*,directory,index):
        return project_step(original(current,state,directory=directory,index=index),current)
    with patch.object(previous,'attempt',attempt):
        return previous.run(item,directory)
