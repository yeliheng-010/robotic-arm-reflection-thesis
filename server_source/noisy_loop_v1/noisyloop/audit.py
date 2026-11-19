"""原物理判据独立复核；额外重建噪声并审查模型可见反馈。"""
import json
from pathlib import Path
from unittest.mock import patch
from semanticfix2.context import enrich,project
from loopstudy import audit as previous
from loopstudy.design import configuration
from noisyloop.feedback import project_step


def clean_step(step,item):
    record=json.loads(Path(step['result_path']).read_text())['records'][0]
    error=record['error']
    feedback=project(enrich(error,attempt=step['index']),configuration(item),attempt=step['index']) if error else None
    return {k:v for k,v in dict(step,feedback=feedback).items() if k not in ('projection_seed','noise_audit')}


def audit(result,item):
    original=previous.physical
    def physical(step,current,reference):
        clean=clean_step(step,current)
        assert project_step(clean,current)==step
        return original(clean,current,reference)
    with patch.object(previous,'physical',physical):
        checked=previous.audit(result,item)
    checked['noise_projections']=sum(s['feedback'] is not None for s in result['attempts'])
    return checked
