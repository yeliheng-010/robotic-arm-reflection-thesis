"""局部引擎记录执行器动作身份，保留原监视器及验收。"""
from semanticfix2.engine import SemanticEngine
from reflection.reflector import Parameters
from posecheck.adapter import capture


def engine_class(item):
    class PoseEngine(SemanticEngine):
        def _attempt(self,*args,**kwargs):
            values = list(args)
            values[5] = Parameters().updated(item['parameters'])
            trace = {}
            with capture(item['yaw_deg'],trace):
                record,report = super()._attempt(*values,**kwargs)
            record['execution_adapter'] = trace
            return record,report
    return PoseEngine
