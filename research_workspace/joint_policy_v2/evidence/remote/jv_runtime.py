"""通用运行入口：每次真实观测绑定自己的候选阶段账本。"""
from unittest.mock import patch
import top_runtime
import jg_runtime
from jg_runtime import GeneralSession as OriginalSession
from jv_context import observation
from jv_choose import choose


class GeneralSession(OriginalSession):
    def _engine(self):
        with patch.object(top_runtime,'filter_context',observation),patch.object(jg_runtime,'choose',choose):
            super()._engine()
