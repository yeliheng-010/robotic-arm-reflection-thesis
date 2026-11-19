"""局部实验引擎只扩充反馈，控制动作仍使用原引擎。"""
from diversity.runtime import DiverseEngine
from reflection.reflector import Parameters
from semanticfix.telemetry import capture
from semanticfix.context import enrich


class SemanticEngine(DiverseEngine):
    def _attempt(self,*args,**kwargs):
        with capture():
            record,report = super()._attempt(*args,**kwargs)
        if report is not None:
            enriched = enrich(report.to_dict(),attempt=record['attempt'])
            report.evidence.update(enriched['evidence'])
            record['error'] = report.to_dict()
        return record,report


def fixed_engine(values):
    class FixedEngine(SemanticEngine):
        def _attempt(self,*args,**kwargs):
            positional = list(args)
            positional[5] = Parameters().updated(values)
            return super()._attempt(*positional,**kwargs)
    return FixedEngine
