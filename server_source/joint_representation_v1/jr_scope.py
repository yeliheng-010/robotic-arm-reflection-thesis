"""仅替换选定终点的等价关节表示；沿用原笛卡尔抓取与放置目标。"""
from contextlib import contextmanager
from unittest.mock import patch
import numpy as np
import goal_search
from js_scope import context as path_context


def wrapper(original, selection):
    def prepose(flow, option):
        row = original(flow,option)
        if np.array_equal(row['q1'],selection['goal']['q1']):
            row = dict(row,q1=selection['path'][-1])
        return row
    return prepose


@contextmanager
def context(selection):
    with patch.object(goal_search,'prepose',wrapper(goal_search.prepose,selection)),path_context(selection):
        yield
