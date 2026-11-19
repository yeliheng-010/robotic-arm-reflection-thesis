"""复算资格和闭环全分母；计划、跳过、实际执行分别统计。"""
import importlib.util
import json
from collections import Counter
from pathlib import Path
from semanticfix2.protocol import sha
from stability.collection_status import atomic
from hardstudy.design import ROOT
from hardstudy.protocol import verify
from hardstudy import qualify,tasks
from hardstudy.outcomes import counts


def helper(folder,name):
    path=ROOT.parent/folder/f'{name}.py'
    spec=importlib.util.spec_from_file_location(folder+'_'+name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def qualification_rows(protocol):
    rows=[]
    for item in protocol['scenes']:
        path=ROOT/'qualification'/item['id']/'result.json'
        if not (path.parent/'summary.json').exists():
            continue
        value=json.loads(path.read_text())
        qualify.audit(value,item)
        saved=json.loads((path.parent/'summary.json').read_text())
        assert saved['status']==value['status'] and saved['executed']==len(value['steps'])
        assert saved['eligible']==value['eligible'] and saved['id']==item['id'] and saved['passed']
        rows.append(dict(item=item,status=value['status'],eligible=value['eligible'],
                         physical_attempts=len(value['steps']),sha256=sha(path)))
    return rows


def metrics(rows):
    output=[]
    for field in ('all','source','factor','split','noise_index','qualification_status'):
        values=['all'] if field=='all' else sorted({r[field] for r in rows})
        for value in values:
            for arm in ('new_rule','hybrid'):
                group=[r for r in rows if r['arm']==arm and (field=='all' or r[field]==value)]
                active=[r for r in group if r['executed']]
                output.append(dict(field=field,value=value,arm=arm,accounted=len(group),executed=len(active),
                    skipped=len(group)-len(active),successes=sum(bool(r['success']) for r in active),
                    **{k:sum(r[k] for r in group) for k in ('attempts','calls','invalid','service_errors')}))
    return output


def write_report(value):
    lines=['# 第三批多机制状态','',
        f"资格条件 {value['qualification_completed']}/200，闭环条目已处理 {value['accounted']}/400。",
        f"闭环实际执行 {value['executed']}，明确跳过 {value['skipped']}；训练批准0。",
        f"资格分布：{value['qualification_statuses']}。",'',
        '| 方法 | 已处理 | 实际执行 | 成功 | 无有效选择 | 接口错误 |',
        '|---|---:|---:|---:|---:|---:|']
    for row in value['metrics']:
        if row['field']=='all':
            lines.append(f"| {row['arm']} | {row['accounted']} | {row['executed']} | {row['successes']} | "
                         f"{row['invalid']} | {row['service_errors']} |")
    lines.extend(['','200个条件来自2组物体容器×5种干预×20个种子；不等于200个独立随机种子。',
        '资格基于无模型的控制运行，未通过的条件不补采。训练候选与开发验证按种子成组隔离。',
        '预留测试种子和已有测试组合未使用。残差带噪，阶段/接触几何仍为理想信息。'])
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n')


def main():
    protocol=verify()
    qualifications=qualification_rows(protocol)
    loaded=[tasks.read(i) for i in protocol['items'] if (ROOT/'tasks'/i['id']/'summary.json').exists()]
    rows=[p[0] for p in loaded]
    results=[p[1] for p in loaded if p[1] is not None]
    old=helper('route_loop_v1','verify')
    noisy=helper('noisy_loop_v1','verify')
    comparison=helper('route_loop_v1','compare')
    transitions=old.transition_rows(results)
    lookup={i['id']:i for i in protocol['items']}
    for row in transitions:
        row['split']=lookup[row['task_id']]['split']
        row['scene_id']=lookup[row['task_id']]['scene_id']
    value=dict(passed=True,complete=len(rows)==400,expected=400,accounted=len(rows),executed=len(results),
        skipped=len(rows)-len(results),qualification_completed=len(qualifications),
        qualification_statuses=dict(Counter(r['status'] for r in qualifications)),
        qualification_physical_attempts=sum(r['physical_attempts'] for r in qualifications),
        metrics=metrics(rows),exposure=noisy.exposure(results),paired_initials=old.paired_initials(results),
        candidate_checks=old.candidate_checks(results),**comparison.compare_physics(results),
        **noisy.paired_methods(results),successful_transitions=len(transitions),training_approved=0,
        test_used=False,rows=rows,qualifications=qualifications,**counts(protocol,results),
        protocol_sha256=sha(ROOT/'protocol.json'))
    atomic(ROOT/'verification.json',value)
    atomic(ROOT/'transitions.json',dict(rows=transitions,training_approved=0))
    write_report(value)
    print(json.dumps({k:v for k,v in value.items() if k not in ('rows','qualifications','metrics')}))
    return value


if __name__=='__main__':
    try:
        main()
    except BaseException as error:
        atomic(ROOT/'verification_failure.json',dict(passed=False,error=repr(error)))
        raise
