"""对外入口：保留baseline和original策略，仅增强含噪观测顶面策略。"""
from cc_runtime import VisibleSession
from jv_runtime import GeneralSession


class Session(GeneralSession):
    def _engine(self):
        if self.case['config']['group']=='baseline' or self.case['strategy']!='observed_top':
            return VisibleSession._engine(self)
        return super()._engine()
