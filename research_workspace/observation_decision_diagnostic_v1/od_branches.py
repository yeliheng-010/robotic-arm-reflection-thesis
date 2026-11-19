"""同一失败快照的固定观测数分支；旧测量不跨状态合并。"""
from loopstudy.actions import choose_rule
from od_common import ROOT,SELECTORS,sha
from od_records import observed,execution_task,load_record


def branch_input(case,level,*,selector):
    assert selector in SELECTORS
    value=observed(case,level)
    rows=value['context']['candidates']
    selected=None
    invalid=None
    record_identity=None
    if selector=='rule':
        selected=choose_rule(rows,value['context']['state'],report=value['context']['feedback']) if rows else None
        invalid=None if rows else 'No executable candidates'
    else:
        task=execution_task(case,level)
        record=load_record(task)
        path=ROOT/'model_records'/f"{task['id']}.json"
        record_identity=dict(path=str(path),sha256=sha(path))
        result=record['result']
        selected=next((r for r in rows if result['valid'] and r['id']==result['action']),None)
        invalid=result['invalid'] if not result['valid'] else None
        assert selected is not None or invalid is not None
    source=value['source']
    return dict(case_id=case['case_id'],level=level,selector=selector,
        source_sha256=source['step']['result_sha256'],source_index=source['step']['index'],
        source_state=source['step']['state'],samples=value['samples'],context=value['context'],
        selected=selected,invalid=invalid,extra_observations=level,model_record=record_identity)
