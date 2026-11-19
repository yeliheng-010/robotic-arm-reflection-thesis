"""适配既有反思接口；保留选择、候选、投影与模板来源。"""
from pathlib import Path
from reflection.reflector import Reflection
from flashnext.client import append
from bounded.candidates import candidates, digest
from bounded.selection import generate


class HybridSelector:
    def __init__(self,directory):
        self.path = Path(directory)/'selection.jsonl'

    def reflect(self,report,parameters,history=()):
        rows = candidates(report.to_dict(),parameters.to_dict(),history)
        event = generate(report.to_dict(),parameters.to_dict(),rows=rows,history=history)
        event.update(candidates=rows,candidate_sha256=digest(rows),
                     explanation_source='deterministic_action_template')
        append(self.path,event)
        if 'parsed' not in event:
            raise RuntimeError('Invalid hybrid selection: '+event.get('error','unknown'))
        return Reflection(**event['parsed'])
