"""来源完整重审；缺测快照选择只依赖模型当时可见信息。"""
from pathlib import Path
from od_common import SOURCE,read
from od_prompts import eligible


def model_rows(scene,method):
    path=SOURCE/'tasks'/scene['id']/method/'result.json'
    trace=read(path)
    rows,cases=[],[]
    for index,d in enumerate(trace['decisions']):
        assert len(d['choices'])==1 and d['choices'][0]['action']!='OBSERVE'
        key=f"{scene['id']}__{method}__d{index}"
        row=dict(id=key,scene_id=scene['id'],seed=scene['seed'],method=method,
            trace_path=str(path),decision_index=index)
        rows.append(row)
        if method=='base_current' and eligible(d['choices'][0]['context']):
            cases.append(dict(row,case_id=f"{scene['id']}__d{index}"))
    return rows,cases


def inventory():
    from am_audit import audit_scene
    parent=read(SOURCE/'manifest.json')
    rows,cases,summaries=[],[],[]
    for scene in parent['scenes']:
        root=SOURCE/'tasks'/scene['id']
        checked=audit_scene(read(root/'result.json'))
        assert checked==read(root/'summary.json')
        summaries.append(checked)
        for method in ('base_current','base_history'):
            new_rows,new_cases=model_rows(scene,method)
            rows.extend(new_rows)
            cases.extend(new_cases)
    assert len(rows)==82 and len(cases)==11 and len(summaries)==24
    return dict(rows=rows,cases=cases,source_summary=summaries)


def source_input(row):
    trace=read(row['trace_path'])
    d=trace['decisions'][row['decision_index']]
    step=trace['attempts'][row['decision_index']]
    assert step['index']==d['after_attempt'] and not step['success']
    assert trace['method']==row['method']
    return dict(trace=trace,decision=d,step=step,messages=d['choices'][0]['event']['request']['messages'])
