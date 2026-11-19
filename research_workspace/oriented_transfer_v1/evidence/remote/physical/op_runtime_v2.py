"""真实规划复算使用进入执行包装前的抓取hook，防止读取尚未选定的轨迹。"""
from unittest.mock import patch
import grasp_process as grasp
import op_runtime

original_selecting=op_runtime.selecting


def selecting(session):
    original=original_selecting(session)
    def choose(flow,**kwargs):
        with patch.object(grasp,'move_to_grasp_pose',kwargs['hooks'][0]):
            return original(flow,**kwargs)
    return choose


class Session(op_runtime.Session):
    def _engine(self):
        with patch.object(op_runtime,'selecting',selecting):
            super()._engine()


class PreviewSession(op_runtime.PreviewSession):
    def _engine(self):
        with patch.object(op_runtime,'selecting',selecting):
            super()._engine()
