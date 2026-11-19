"""原始物理判据与扰动可见反馈分别重建。"""
import json
from pathlib import Path
from unittest.mock import patch
from semanticfix2.context import enrich,project
from loopstudy import audit as previous
from hardstudy.design import configuration
from hardstudy.feedback import project_step
from hardstudy.bridge import bound
from hardstudy.intervention import audit as audit_intervention


def clean_step(step,item):
    record=json.loads(Path(step['result_path']).read_text())['records'][0]
    error=record['error']
    feedback=project(enrich(error,attempt=step['index']),configuration(item),attempt=step['index']) if error else None
    return {k:v for k,v in dict(step,feedback=feedback).items() if k not in ('projection_seed','noise_audit')}


def audit(result,item):
    original=previous.physical
    def physical(step,current,reference):
        audit_intervention(step,current)
        clean=clean_step(step,current)
        assert project_step(clean,current)==step
        return original(clean,current,reference)
    with bound(item),patch.object(previous,'physical',physical):
        checked=previous.audit(result,item)
    checked['noise_projections']=sum(s['feedback'] is not None for s in result['attempts'])
    return checked
